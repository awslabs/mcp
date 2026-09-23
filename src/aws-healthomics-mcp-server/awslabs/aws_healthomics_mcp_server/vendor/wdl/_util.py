# misc utility functions...

import sys
import os
import json
import logging
import signal
import threading
import time
import fcntl
import shutil
import uuid
import decimal
from time import sleep
from datetime import datetime
from contextlib import contextmanager, AbstractContextManager
from typing import (
    Tuple,
    Dict,
    Set,
    Iterator,
    List,
    TypeVar,
    Generic,
    Optional,
    Callable,
    Generator,
    Any,
    TYPE_CHECKING,
)
from types import FrameType
from pythonjsonlogger import jsonlogger

if TYPE_CHECKING:
    from . import Env, Value

T = TypeVar("T")

__all__: List[str] = []


def export(obj: T) -> T:
    __all__.append(obj.__name__)  # type: ignore
    return obj


@export
def strip_leading_whitespace(txt: str) -> Tuple[int, str]:
    # Given a multi-line string, determine the largest w such that each line
    # begins with at least w whitespace characters. Return w and the string
    # with w characters removed from the beginning of each line.
    lines = txt.split("\n")

    to_strip = None
    for line in lines:
        lsl = len(line.lstrip())
        if lsl:
            c = len(line) - lsl
            assert c >= 0
            if to_strip is None or to_strip > c:
                to_strip = c
            # TODO: do something about mixed tabs & spaces

    if not to_strip:
        return (0, txt)

    for i, line_i in enumerate(lines):
        if line_i.lstrip():
            lines[i] = line_i[to_strip:]

    return (to_strip, "\n".join(lines))


@export
class AdjM(Generic[T]):
    # A sparse adjacency matrix for topological sorting
    # which we should not have implemented ourselves
    _forward: Dict[T, Set[T]]
    _reverse: Dict[T, Set[T]]
    _unconstrained: Set[T]

    def __init__(self) -> None:
        self._forward = dict()
        self._reverse = dict()
        self._unconstrained = set()

    def sinks(self, source: T) -> Iterator[T]:
        for sink in self._forward.get(source, []):
            yield sink

    def sources(self, sink: T) -> Iterator[T]:
        for source in self._reverse.get(sink, []):
            yield source

    @property
    def nodes(self) -> Iterator[T]:
        for node in self._forward:
            yield node

    @property
    def unconstrained(self) -> Iterator[T]:
        for n in self._unconstrained:
            assert not self._reverse[n]
            yield n

    def add_node(self, node: T) -> None:
        if node not in self._forward:
            assert node not in self._reverse
            self._forward[node] = set()
            self._reverse[node] = set()
            self._unconstrained.add(node)
        else:
            assert node in self._reverse

    def add_edge(self, source: T, sink: T) -> None:
        self.add_node(source)
        self.add_node(sink)
        if sink not in self._forward[source]:
            self._forward[source].add(sink)
            self._reverse[sink].add(source)
            if sink in self._unconstrained:
                self._unconstrained.remove(sink)
        else:
            assert source in self._reverse[sink]
            assert sink not in self._unconstrained

    def remove_edge(self, source: T, sink: T) -> None:
        if source in self._forward and sink in self._forward[source]:
            self._forward[source].remove(sink)
            self._reverse[sink].remove(source)
            if not self._reverse[sink]:
                self._unconstrained.add(sink)
        else:
            assert not (sink in self._reverse and source in self._reverse[sink])

    def remove_node(self, node: T) -> None:
        for source in list(self.sources(node)):
            self.remove_edge(source, node)
        for sink in list(self.sinks(node)):
            self.remove_edge(node, sink)
        del self._forward[node]
        del self._reverse[node]
        self._unconstrained.remove(node)


@export
def topsort(adj: AdjM[T]) -> List[T]:
    # topsort node IDs in adj (destroys adj)
    # if there's a cycle, raises err: StopIteration with err.node = ID of a
    # node involved in a cycle.
    ans = []
    node = next(adj.unconstrained, None)
    while node:
        adj.remove_node(node)
        ans.append(node)
        node = next(adj.unconstrained, None)
    node = next(adj.nodes, None)
    if node:
        err = StopIteration()
        setattr(err, "node", node)
        raise err
    return ans


@export
def write_atomic(contents: str, filename: str, end: str = "\n") -> None:
    # 04-JUN-2021 changed to use UUID filename instead of relying on open(tn, "x") in case network
    # filesystem is wonky with O_EXCL.
    tn = filename + ".tmp." + str(uuid.uuid1())
    with open(tn, "w") as outfile:
        print(contents, file=outfile, end=end)
    os.rename(tn, filename)


@export
def rmtree_atomic(path: str) -> None:
    """
    Recursively delete a directory (or single file) after first renaming it to a temporary name in
    the same parent directory. The atomic rename step ensures a "partial" directory won't be left
    behind in its original location, should anything go wrong whilst deleting its contents.
    """
    path = os.path.abspath(path)
    assert path and path.strip("/")
    tmp_path = os.path.join(os.path.dirname(path), ".rmtree_atomic." + str(uuid.uuid1()))
    os.renames(path, tmp_path)
    shutil.rmtree(tmp_path)


@export
def symlink_force(src: str, dst: str, hard: bool = False) -> None:
    """
    Create a symbolic pointing to src named dst, atomically replacing any existing symbolic or
    hard link at dst.
    """
    assert not dst.endswith("/")
    tn = dst + ".tmp." + str(uuid.uuid1())
    if hard:
        os.link(src, tn)
    else:
        os.symlink(src, tn)
    os.rename(tn, dst)


@export
def link_force(src: str, dst: str) -> None:
    """
    Create a hard link pointing to src named dst, atomically replacing any existing symbolic or hard
    link at dst.
    """
    symlink_force(src, dst, hard=True)


@export
def write_values_json(
    values_env: "Env.Bindings[Value.Base]", filename: str, namespace: str = ""
) -> None:
    from . import values_to_json

    write_atomic(
        json.dumps(
            values_to_json(values_env, namespace=namespace),
            indent=2,
            sort_keys=True,
        ),
        filename,
    )


@export
def provision_run_dir(name: str, parent_dir: Optional[str], last_link: bool = False) -> str:
    here = (
        (parent_dir in [".", "./"] or parent_dir.endswith("/.") or parent_dir.endswith("/./"))
        if parent_dir
        else False
    )
    parent_dir = os.path.abspath(parent_dir or os.getcwd())

    run_dir = None
    if here:
        # user wants to use parent_dir exactly
        run_dir = parent_dir
        os.makedirs(run_dir, exist_ok=True)
        parent_dir = os.path.dirname(parent_dir)
    else:
        # create timestamp-named directory
        while not run_dir:
            run_dir = os.path.join(
                parent_dir, datetime.today().strftime("%Y%m%d_%H%M%S") + "_" + name
            )
            try:
                os.makedirs(run_dir, exist_ok=False)
            except FileExistsError:
                run_dir = None
                sleep(0.5)
    assert run_dir

    # update the _LAST link
    if last_link and run_dir != parent_dir:
        last_link_name = os.path.join(parent_dir, "_LAST")
        if os.path.islink(last_link_name) or not (here or os.path.lexists(last_link_name)):
            symlink_force(os.path.basename(run_dir), last_link_name)

    return run_dir


@export
class StructuredLogMessage:
    message: str
    kwargs: Dict[str, Any]

    # from https://docs.python.org/3.8/howto/logging-cookbook.html#implementing-structured-logging
    def __init__(self, _message: str, **kwargs) -> None:
        self.message = _message
        self.kwargs = kwargs

    def __str__(self) -> str:
        return f"{self.message} :: {', '.join(k + ': ' + json.dumps(v) for k, v in self.kwargs.items())}"


class StructuredLogMessageJSONFormatter(jsonlogger.JsonFormatter):
    "JSON formatter for StructuredLogMessages"

    def format(self, rec: logging.LogRecord) -> str:
        if isinstance(rec.msg, StructuredLogMessage):
            ans = {"level": rec.levelname, "message": rec.msg.message}
            for k, v in rec.msg.kwargs.items():
                if k not in ans:
                    ans[k] = v
            rec.msg = ans
        return super().format(rec)

    def add_fields(
        self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = round(record.created, 3)
        log_record["source"] = record.name
        log_record["level"] = record.levelname
        log_record["levelno"] = record.levelno


VERBOSE_LEVEL = 15
__all__.append("VERBOSE_LEVEL")
logging.addLevelName(VERBOSE_LEVEL, "VERBOSE")


def verbose(self, message, *args, **kws):
    if self.isEnabledFor(VERBOSE_LEVEL):
        self._log(VERBOSE_LEVEL, message, args, **kws)


logging.Logger.verbose = verbose  # type: ignore
NOTICE_LEVEL = 25
__all__.append("NOTICE_LEVEL")
logging.addLevelName(NOTICE_LEVEL, "NOTICE")


def notice(self, message, *args, **kws):
    if self.isEnabledFor(NOTICE_LEVEL):
        self._log(NOTICE_LEVEL, message, args, **kws)


logging.Logger.notice = notice  # type: ignore


@export
class ANSI:
    # https://gist.github.com/RabaDabaDoba/145049536f815903c79944599c6f952a
    # https://espterm.github.io/docs/VT100%20escape%20codes.html
    CLEAR: str = "\x1b[2K\r"
    RESET: str = "\x1b[0m"
    BOLD: str = "\x1b[1m"

    RED: str = "\x1b[0;31m"
    BRED: str = "\x1b[1;31m"
    HRED: str = "\x1b[0;91m"
    BHRED: str = "\x1b[1;91m"

    HIDE_CURSOR: str = "\x1b[?25l"
    SHOW_CURSOR: str = "\x1b[?25h"


def _ansilen(parts: List[str]) -> int:
    return sum([len(s) for s in parts if s[0] != "\x1b"])


LOGGING_FORMAT = "%(asctime)s.%(msecs)03d %(name)s %(levelname)s %(message)s"
COLORED_LOGGING_FORMAT = "%(asctime)s.%(msecs)03d %(name)s %(message)s"  # colors obviate levelname
__all__.append("LOGGING_FORMAT")


@export
@contextmanager
def configure_logger(
    force_tty: bool = False, json: bool = False
) -> Iterator[Callable[[List[str]], None]]:
    """
    contextmanager to set up the root/stderr logger; yields a function to set the status line at
    the bottom of the screen (if stderr isatty, else it does nothing)
    """
    import coloredlogs  # delayed heavy import

    class _StatusLineStandardErrorHandler(coloredlogs.StandardErrorHandler):
        """
        This subclass augments coloredlogs.StandardErrorHandler to maintain a "status line" which
        remains in place at the bottom of the screen as log records scroll by. The content of the
        status line can be set at any time. It will be truncated to the terminal width.
        """

        _singleton: "Optional[_StatusLineStandardErrorHandler]" = None
        _status: str = ""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            assert not self.__class__._singleton
            self.__class__._singleton = self

        def emit(self, record: logging.LogRecord) -> None:
            self.acquire()
            try:
                sys.stderr.write(ANSI.CLEAR)
                super().emit(record)
                self.emit_status()
            finally:
                self.release()

        def emit_status(self) -> None:
            self.acquire()
            try:
                sys.stderr.write(ANSI.CLEAR + self._status + ANSI.RESET)
                self.flush()
            finally:
                self.release()

        def set_status(self, new_status: List[str]) -> None:
            cols = shutil.get_terminal_size().columns
            if _ansilen(new_status) > cols:
                new_status = new_status.copy()
                while new_status and (_ansilen(new_status) > cols or new_status[-1][0] == "\x1b"):
                    new_status.pop()
            self._status = "".join(new_status)
            self.emit_status()

    logger = logging.getLogger()

    if json:
        logger.handlers[0].setFormatter(StructuredLogMessageJSONFormatter())
        yield (lambda ignore: None)
    else:
        level_styles = {}
        field_styles = {}
        fmt = LOGGING_FORMAT
        tty = force_tty or (sys.stderr.isatty() and "NO_COLOR" not in os.environ)

        if tty:
            level_styles = dict(coloredlogs.DEFAULT_LEVEL_STYLES)
            level_styles["debug"]["color"] = 242
            level_styles["notice"] = {"color": "green", "bold": True}
            level_styles["error"]["bold"] = True
            level_styles["warning"]["bold"] = True
            level_styles["info"] = {}
            field_styles = dict(coloredlogs.DEFAULT_FIELD_STYLES)
            field_styles["asctime"] = {"color": "blue"}
            field_styles["name"] = {"color": "magenta"}
            fmt = COLORED_LOGGING_FORMAT

            # monkey-patch _StatusLineStandardErrorHandler over coloredlogs.StandardErrorHandler for
            # coloredlogs.install() to instantiate
            coloredlogs.StandardErrorHandler = _StatusLineStandardErrorHandler  # type: ignore
            sys.stderr.write(ANSI.HIDE_CURSOR)  # hide cursor

        try:
            coloredlogs.install(
                level=logger.getEffectiveLevel(),
                logger=logger,
                level_styles=level_styles,
                field_styles=field_styles,
                fmt=fmt,
            )
            yield (
                lambda status: (
                    _StatusLineStandardErrorHandler._singleton.set_status(status)
                    if _StatusLineStandardErrorHandler._singleton
                    else None
                )
            )
        finally:
            if tty:
                sys.stderr.write(ANSI.CLEAR)  # wipe the status line
                sys.stderr.write(ANSI.SHOW_CURSOR)  # un-hide cursor


# NOTE: upstream miniwdl's PygtailLogger (task-log streaming via the GPL-licensed `pygtail`
# package) was removed here during vendoring — it is runtime/task-execution-only and is never
# called by the parsing/lint code paths vendored in this directory. See VENDORED.md.


_terminating: Optional[bool] = None
_terminating_lock: threading.Lock = threading.Lock()


@export
@contextmanager
def TerminationSignalFlag(logger: logging.Logger) -> Iterator[Callable[[], bool]]:
    """
    Context manager installing termination signal handlers (SIGTERM, SIGQUIT, SIGINT, SIGHUP) which
    set a global flag indicating whether such a signal has been received. Yields a function which
    returns this flag.

    Should be opened on the main thread wrapping all the desired operations. Once this is so, more
    instances can be opened on any thread without interfering with each other, as long as they're
    nested within the main one.
    """
    signals = [
        signal.SIGTERM,
        signal.SIGQUIT,
        signal.SIGINT,
        signal.SIGHUP,
        signal.SIGUSR1,
        signal.SIGALRM,  # used in unit test
        # don't trap SIGPIPE -- Python has a default handler to generate BrokenPipeError
    ]

    def handle_signal(sig: int, frame: Optional[FrameType]) -> None:
        global _terminating
        if not _terminating:
            if sig != signal.SIGUSR1:
                logger.critical(StructuredLogMessage("aborting workflow", signal=sig))
            else:
                # SIGUSR1 comes from ourselves, as the signal to abort after something else has
                # already gone wrong
                logger.notice("aborting workflow")
        _terminating = True

    global _terminating
    global _terminating_lock
    restore_signal_handlers = None
    with _terminating_lock:
        if _terminating is None:
            restore_signal_handlers = dict(
                (sig, signal.signal(sig, handle_signal)) for sig in signals
            )
            _terminating = False
    try:
        yield lambda: _terminating or False
    finally:
        if restore_signal_handlers:
            with _terminating_lock:
                for sig, handler in restore_signal_handlers.items():
                    signal.signal(sig, handler)
                _terminating = None


byte_size_units = {
    "B": 1,
    "K": 1000,
    "KB": 1000,
    "Ki": 1024,
    "KiB": 1024,
    "M": 1000000,
    "MB": 1000000,
    "Mi": 1048576,
    "MiB": 1048576,
    "G": 1000000000,
    "GB": 1000000000,
    "Gi": 1073741824,
    "GiB": 1073741824,
    "T": 1000000000000,
    "TB": 1000000000000,
    "Ti": 1099511627776,
    "TiB": 1099511627776,
}


@export
def parse_byte_size(s: str) -> int:
    """
    convert strings like "2000", "4G", "1.5 TiB" to a positive number of bytes
    """

    s = s.strip()
    N = None
    unit = None
    for i in range(len(s)):
        if s[i].isdigit() or s[i] == ".":
            N = float(s[: i + 1])
            unit = s[i + 1 :].lstrip()
        else:
            break
    if N and unit:
        if unit in byte_size_units:
            N *= byte_size_units[unit]
        else:
            N = None
    if N is None or N < 0:
        raise ValueError("invalid byte size string, " + s)
    return int(N)


@export
def pathsize(path: str) -> int:
    """
    get byte size of file, or total size of all files under directory & subdirectories (symlinks
    excluded)
    """

    if not os.path.isdir(path):
        return os.path.getsize(path)

    def raiser(exc: OSError):
        raise exc

    ans = 0
    for root, subdirs, files in os.walk(path, onerror=raiser, followlinks=False):
        for fn in files:
            fn = os.path.join(root, fn)
            if not os.path.islink(fn):
                ans += os.path.getsize(fn)

    return ans


def splitall(path: str) -> List[str]:
    """
    https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s16.html
    """
    allparts: List[str] = []
    while True:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


@export
def path_really_within(lhs: str, rhs: str) -> bool:
    """
    After resolving symlinks, is path lhs either equal to or nested within path rhs?
    """
    lhs_cmp = splitall(os.path.realpath(lhs))
    rhs_cmp = splitall(os.path.realpath(rhs))
    return len(lhs_cmp) >= len(rhs_cmp) and lhs_cmp[: len(rhs_cmp)] == rhs_cmp


@export
def chmod_R_plus(path: str, file_bits: int = 0, dir_bits: int = 0) -> None:
    """
    recursive chmod to add permission bits (possibly different for files and subdirectiores)
    does not follow symlinks
    """

    def do1(path1: str, bits: int) -> None:
        assert 0 <= bits < 0o10000
        if not os.path.islink(path1) and path_really_within(path1, path):
            os.chmod(path1, (os.stat(path1).st_mode & 0o7777) | bits)

    def raiser(exc: OSError):
        raise exc

    if os.path.isdir(path):
        do1(path, dir_bits)
        for root, subdirs, files in os.walk(path, onerror=raiser, followlinks=False):
            for dn in subdirs:
                do1(os.path.join(root, dn), dir_bits)
            for fn in files:
                do1(os.path.join(root, fn), file_bits)
    else:
        do1(path, file_bits)


@export
@contextmanager
def LoggingFileHandler(
    logger: logging.Logger, filename: str, json: bool = False
) -> Iterator[logging.FileHandler]:
    """
    Context manager which opens a logging.FileHandler and adds it to the logger; on exit, closes
    the log file and removes the handler.
    """
    fh = logging.FileHandler(filename)
    fh.setFormatter(
        StructuredLogMessageJSONFormatter()
        if json
        else logging.Formatter(LOGGING_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    )
    try:
        logger.addHandler(fh)
        yield fh
    finally:
        fh.flush()
        fh.close()
        logger.removeHandler(fh)


@export
@contextmanager
def compose_coroutines(
    generators: List[Callable[[Any], Generator[Any, Any, None]]], x: Any
) -> Iterator[Generator[Any, Any, None]]:
    """
    Coroutine (generator) which composes several other coroutines to run in lockstep for one or
    more "rounds." On each round, caller sends a value, which is sent to the first coroutine; the
    value it yields is sent to the second coroutine; and so on until finally the value yielded by
    the last coroutine is yielded back to the caller. Exceptions propagate in the same way, so a
    coroutine can catch and manipulate (but not suppress) an exception raised by the caller or by
    one of the other coroutines.
    """

    def _impl() -> Generator[Any, Any, None]:
        # start the coroutines by invoking each generator and taking the first value it yields
        nonlocal x
        cors = []
        try:
            for gen in generators:
                cor = gen(x)
                x = next(cor)
                cors.append(cor)
            while True:  # GeneratorExit will break
                # yield to caller and get updated value back
                try:
                    x = yield x
                except Exception as exn:
                    for cor in cors:
                        try:
                            cor.throw(exn)
                        except Exception as exn2:
                            exn = exn2
                    raise exn
                # pass value through coroutines
                cor_exn = None
                for cor in cors:
                    try:
                        if not cor_exn:
                            x = cor.send(x)
                        else:
                            cor.throw(cor_exn)
                    except Exception as exn2:
                        cor_exn = exn2
                if cor_exn:
                    raise cor_exn
        finally:
            close_exn = None
            for cor in cors:
                try:
                    cor.close()
                except Exception as exn2:
                    close_exn = close_exn or exn2
            if close_exn:
                raise close_exn

    # this outer contextmanager is for closing the coroutines promptly and propagating any caller
    # exceptions back through them. see: https://stackoverflow.com/a/58854646
    chain = _impl()
    try:
        yield chain
    except Exception as exn:
        chain.throw(exn)
        raise
    finally:
        chain.close()


@export
class FlockHolder(AbstractContextManager):
    """
    Context manager exposing a method to take an advisory lock on a file (flock) and hold it until
    context exit. The context manager is reentrant; locks are released upon exit of the outermost
    nested context.
    """

    _lock: threading.Lock
    _flocks: Dict[str, Tuple[int, bool]]
    _entries: int
    _logger: logging.Logger

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._lock = threading.Lock()
        self._flocks = {}
        self._entries = 0
        self._logger = (
            logger.getChild("FlockHolder") if logger else logging.getLogger("FlockHolder")
        )

    def __enter__(self) -> "FlockHolder":
        assert self._entries > 0 or not self._flocks
        self._entries += 1
        return self

    def __exit__(self, *exc_details) -> None:
        assert self._entries > 0, "FlockHolder context exited prematurely"
        self._entries -= 1
        if self._entries == 0:
            exn = None
            with self._lock:
                for fn, (fd, exclusive) in self._flocks.items():
                    self._logger.debug(StructuredLogMessage("close", file=fn, exclusive=exclusive))
                    try:
                        os.close(fd)
                    except Exception as exn2:
                        exn = exn or exn2
                self._flocks = {}
            if exn:
                raise exn

    def __del__(self) -> None:
        assert self._entries == 0 and not self._flocks, "FlockHolder context was not exited"

    def flock(
        self,
        filename: str,
        mode: Optional[int] = None,
        exclusive: bool = False,
        wait: bool = False,
    ) -> int:
        """
        Open a file and an advisory lock on it. The file is closed and the lock released upon exit
        of the outermost context. Returns the open file descriptor, which the caller shouldn't
        close (managed by the object).

        :param filename: file to open & lock
        :param mode: os.open() mode flags, default: OS.O_RDWR if exclusive else os.O_RDONLY
        :param exclusive: True to open an exclusive lock (default: shared lock)
        :param wait: True to wait as long as needed to obtain the lock, otherwise (default) raise
                     OSError if the lock isn't available immediately. Self-deadlock is possible;
                     see Python fcntl.flock docs for further details.
        """
        assert self._entries, "FlockHolder.flock() used out of context"
        while True:
            realfilename = os.path.realpath(filename)
            with self._lock:  # only needed to synchronize self._flocks
                if realfilename in self._flocks and not exclusive:
                    self._logger.debug(
                        StructuredLogMessage(
                            "reuse prior flock",
                            filename=filename,
                            realpath=realfilename,
                            exclusive=self._flocks[realfilename][1],
                        )
                    )
                    return self._flocks[realfilename][0]
                openfile = os.open(
                    realfilename,
                    mode if mode is not None else (os.O_RDWR if exclusive else os.O_RDONLY),
                )
                try:
                    op = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                    if not wait:
                        op |= fcntl.LOCK_NB
                    self._logger.debug(
                        StructuredLogMessage(
                            "flock",
                            file=filename,
                            realpath=realfilename,
                            exclusive=exclusive,
                            wait=wait,
                        )
                    )
                    fcntl.flock(openfile, op)
                    # the flock will release whenever we ultimately openfile.close()

                    file_st = os.stat(openfile)

                    # Even if all concurrent processes obey the advisory flocks, the filename link
                    # could have been replaced or removed in the duration between our open() and
                    # fcntl() syscalls.
                    # - if it was removed, the following os.stat will trigger FileNotFoundError,
                    #   which is reasonable to propagate.
                    # - if it was replaced, the subsequent condition won't hold, and we'll loop
                    #   around to try again on the replacement file.
                    filename_st = os.stat(realfilename)
                    self._logger.debug(
                        StructuredLogMessage(
                            "flocked",
                            file=filename,
                            realpath=realfilename,
                            exclusive=exclusive,
                            name_inode=filename_st.st_ino,
                            fd_inode=file_st.st_ino,
                        )
                    )
                    if (
                        filename_st.st_dev == file_st.st_dev
                        and filename_st.st_ino == file_st.st_ino
                    ):
                        assert realfilename not in self._flocks
                        self._flocks[realfilename] = (openfile, exclusive)
                        return openfile
                except:
                    os.close(openfile)
                    raise
                os.close(openfile)  # NOT finally -- for next while-loop iteration


def bump_atime(filename: str) -> None:
    fd = os.open(os.path.realpath(filename), os.O_RDONLY)
    try:
        file_st = os.stat(fd)
        os.utime(fd, ns=(int(time.time() * 1e9), file_st.st_mtime_ns))
    finally:
        os.close(fd)


@export
class RepeatTimer(threading.Timer):
    def run(self) -> None:
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def currently_in_container() -> bool:
    # https://github.com/containers/podman/issues/3586#issuecomment-512191693
    try:
        with open(f"/proc/{os.getpid()}/mounts") as infile:
            return " / overlay" in infile.read()
    except Exception:
        return False


@export
def round_half_up(x: float) -> int:
    """
    Round a float to the nearest integer, rounding half up.
    """
    return int(decimal.Decimal(x).to_integral_value(rounding=decimal.ROUND_HALF_UP))
