"""
Unit tests for path validation utilities.
"""

import os

import pytest

from awslabs.ecs_mcp_server.utils import path_validation
from awslabs.ecs_mcp_server.utils.path_validation import BLOCKED_DIRS, validate_path

HOME = os.path.realpath(os.path.expanduser("~"))


class TestBlockedDirs:
    """Tests for the sensitive directory blocklist."""

    @pytest.mark.parametrize(
        "expected",
        [
            os.path.join(HOME, ".aws"),
            os.path.join(HOME, ".ssh"),
            os.path.join(HOME, ".kube"),
            os.path.join(HOME, ".gnupg"),
            os.path.join(HOME, ".docker"),
            "/etc",
            "/root",
            "/var/lib",
        ],
    )
    def test_blocklist_covers_expected_location(self, expected):
        """Every location reported by AWS Security is on the blocklist."""
        assert os.path.realpath(expected) in BLOCKED_DIRS

    def test_blocklist_entries_are_fully_resolved(self):
        """Entries are stored resolved so symlinked system paths still match."""
        for blocked in BLOCKED_DIRS:
            assert blocked == os.path.realpath(blocked)

    def test_blocklist_has_no_duplicates(self):
        """The two home sources normally agree, so entries must be deduplicated."""
        assert len(BLOCKED_DIRS) == len(set(BLOCKED_DIRS))

    def test_home_dirs_includes_expanded_home(self):
        """The blocklist is anchored on the home directory $HOME points at."""
        assert os.path.expanduser("~") in path_validation._home_dirs()

    @pytest.mark.skipif(not hasattr(os, "getuid"), reason="requires a POSIX password database")
    def test_home_dirs_survives_redirected_home(self, tmp_path, monkeypatch):
        """
        A redirected $HOME cannot hide the account's real home directory.

        The password database is consulted as a second source so that a server
        started with $HOME pointing elsewhere still protects the real ~/.aws.
        """
        import pwd

        real_home = pwd.getpwuid(os.getuid()).pw_dir
        monkeypatch.setenv("HOME", str(tmp_path))

        homes = path_validation._home_dirs()

        assert str(tmp_path) in homes
        assert real_home in homes

    @pytest.mark.skipif(not hasattr(os, "getuid"), reason="requires a POSIX password database")
    def test_home_dirs_falls_back_to_env_home_when_password_db_fails(self, monkeypatch):
        """An account missing from the password database leaves $HOME as the source."""
        import pwd

        def raise_key_error(*_args, **_kwargs):
            raise KeyError("uid not found in password database")

        monkeypatch.setattr(pwd, "getpwuid", raise_key_error)

        assert path_validation._home_dirs() == (os.path.expanduser("~"),)

    @pytest.mark.skipif(not hasattr(os, "getuid"), reason="requires a POSIX password database")
    def test_blocklist_covers_both_home_sources(self, tmp_path, monkeypatch):
        """Sensitive directories are blocked under every candidate home."""
        import pwd

        real_home = pwd.getpwuid(os.getuid()).pw_dir
        monkeypatch.setenv("HOME", str(tmp_path))

        blocked = path_validation._resolve_blocked_dirs()

        assert os.path.realpath(os.path.join(str(tmp_path), ".aws")) in blocked
        assert os.path.realpath(os.path.join(real_home, ".aws")) in blocked


class TestValidatePathRejectsSensitivePaths:
    """Tests that paths related to sensitive directories are rejected."""

    @pytest.mark.parametrize("blocked", BLOCKED_DIRS)
    def test_rejects_blocked_directory_itself(self, blocked):
        """The sensitive directory itself is rejected."""
        with pytest.raises(ValueError) as excinfo:
            validate_path(blocked)
        assert blocked in str(excinfo.value)

    @pytest.mark.parametrize("blocked", BLOCKED_DIRS)
    def test_rejects_path_inside_blocked_directory(self, blocked):
        """A file inside a sensitive directory is rejected."""
        with pytest.raises(ValueError):
            validate_path(os.path.join(blocked, "credentials"))

    def test_rejects_tilde_form_of_blocked_directory(self):
        """A tilde path is expanded before the blocklist check."""
        with pytest.raises(ValueError):
            validate_path("~/.aws")

    def test_rejects_file_inside_tilde_form_of_blocked_directory(self):
        """A tilde path to a file inside a sensitive directory is rejected."""
        with pytest.raises(ValueError):
            validate_path("~/.aws/credentials")

    def test_rejects_relative_path_resolving_into_blocked_directory(self, monkeypatch):
        """A relative path is resolved before the blocklist check."""
        monkeypatch.chdir(HOME)
        with pytest.raises(ValueError):
            validate_path(".aws")

    def test_rejects_upward_traversal_into_blocked_directory(self):
        """Traversal components cannot be used to reach a sensitive directory."""
        with pytest.raises(ValueError):
            validate_path(os.path.join(HOME, "some-app", "..", ".aws"))

    def test_rejects_symlink_pointing_into_blocked_directory(self, tmp_path):
        """Symlinks are resolved, so they cannot be used to reach a sensitive directory."""
        link = tmp_path / "innocent-looking-app"
        os.symlink(os.path.join(HOME, ".aws"), str(link))

        with pytest.raises(ValueError):
            validate_path(str(link))

    def test_rejects_filesystem_root(self):
        """The filesystem root is rejected because it contains sensitive directories."""
        with pytest.raises(ValueError):
            validate_path("/")

    def test_rejects_home_directory(self):
        """The home directory is rejected because it contains sensitive directories."""
        with pytest.raises(ValueError):
            validate_path(HOME)

    def test_rejects_ancestor_of_blocked_directory(self):
        """An ancestor of a sensitive directory is rejected."""
        with pytest.raises(ValueError):
            validate_path(os.path.dirname(os.path.realpath("/var/lib")))

    def test_error_message_names_the_offending_directory(self):
        """The error explains which sensitive directory caused the rejection."""
        with pytest.raises(ValueError) as excinfo:
            validate_path("~/.ssh/id_rsa")
        assert os.path.realpath(os.path.join(HOME, ".ssh")) in str(excinfo.value)


class TestValidatePathAcceptsSafePaths:
    """Tests that ordinary application paths remain usable."""

    def test_accepts_existing_absolute_path(self, tmp_path):
        """An ordinary absolute path is returned resolved."""
        assert validate_path(str(tmp_path)) == os.path.realpath(str(tmp_path))

    def test_accepts_relative_path_and_returns_absolute(self, tmp_path, monkeypatch):
        """Relative paths stay supported and are resolved to absolute paths."""
        app_dir = tmp_path / "my-app"
        app_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        assert validate_path("my-app") == os.path.realpath(str(app_dir))

    def test_accepts_dot_relative_path(self, tmp_path, monkeypatch):
        """A './' prefixed path is supported."""
        app_dir = tmp_path / "my-app"
        app_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        assert validate_path("./my-app") == os.path.realpath(str(app_dir))

    def test_accepts_nonexistent_path_by_default(self, tmp_path):
        """Existence is not required unless the caller asks for it."""
        target = tmp_path / "not-created-yet"

        assert validate_path(str(target)) == os.path.realpath(str(target))

    def test_accepts_sibling_of_blocked_directory(self):
        """A directory whose name merely starts like a blocked one is allowed."""
        sibling = os.path.join(HOME, ".awsome-app")

        assert validate_path(sibling) == os.path.realpath(sibling)

    def test_accepts_path_with_blocked_prefix_but_different_directory(self):
        """'/etcetera' is not '/etc' and must not be blocked by prefix matching."""
        assert validate_path("/etcetera") == os.path.realpath("/etcetera")

    def test_accepts_subdirectory_of_home(self):
        """An application directory under the home directory is allowed."""
        app_dir = os.path.join(HOME, "projects", "my-app")

        assert validate_path(app_dir) == os.path.realpath(app_dir)

    def test_resolves_symlink_to_safe_directory(self, tmp_path):
        """A symlink to a safe directory resolves to its target."""
        target = tmp_path / "real-app"
        target.mkdir()
        link = tmp_path / "link-to-app"
        os.symlink(str(target), str(link))

        assert validate_path(str(link)) == os.path.realpath(str(target))


class TestValidatePathExistence:
    """Tests for the must_exist behaviour."""

    def test_must_exist_accepts_existing_path(self, tmp_path):
        """An existing path passes when existence is required."""
        assert validate_path(str(tmp_path), must_exist=True) == os.path.realpath(str(tmp_path))

    def test_must_exist_rejects_missing_path(self, tmp_path):
        """A missing path is rejected when existence is required."""
        with pytest.raises(ValueError) as excinfo:
            validate_path(str(tmp_path / "missing"), must_exist=True)
        assert "does not exist" in str(excinfo.value)

    def test_blocklist_is_checked_before_existence(self):
        """
        A sensitive path that does not exist is reported as sensitive.

        Callers have historically special-cased "does not exist" errors in order to
        create missing directories, so a sensitive path must never be reported that
        way or the rejection could be swallowed.
        """
        with pytest.raises(ValueError) as excinfo:
            validate_path(os.path.join(HOME, ".aws", "definitely-not-created"), must_exist=True)
        assert "does not exist" not in str(excinfo.value)


class TestValidatePathInputHandling:
    """Tests for malformed input."""

    @pytest.mark.parametrize("value", ["", "   ", "\t\n"])
    def test_rejects_blank_path(self, value):
        """Blank paths are rejected rather than resolving to the working directory."""
        with pytest.raises(ValueError) as excinfo:
            validate_path(value)
        assert "non-empty string" in str(excinfo.value)

    @pytest.mark.parametrize("value", [None, 123, [], {}])
    def test_rejects_non_string_path(self, value):
        """Non-string input is rejected with a clear error."""
        with pytest.raises(ValueError) as excinfo:
            validate_path(value)
        assert "non-empty string" in str(excinfo.value)


class TestCaseInsensitiveFilesystems:
    """
    Tests for case handling, which differs by platform.

    macOS and Windows filesystems are case-insensitive by default, so a case
    variant of a blocked directory names the same directory there and has to be
    rejected. Linux filesystems are case-sensitive, where the same variant is a
    genuinely different directory.
    """

    def test_normalize_folds_case_on_case_insensitive_filesystems(self, monkeypatch):
        """Comparison keys are case-folded where the filesystem ignores case."""
        monkeypatch.setattr(path_validation, "_CASE_INSENSITIVE_FS", True)

        assert (
            path_validation._normalize("/Home/User/.AWS")
            == os.path.normcase("/Home/User/.AWS").casefold()
        )

    def test_normalize_preserves_case_on_case_sensitive_filesystems(self, monkeypatch):
        """Comparison keys preserve case where the filesystem distinguishes it."""
        monkeypatch.setattr(path_validation, "_CASE_INSENSITIVE_FS", False)

        assert path_validation._normalize("/Home/User/.AWS") == os.path.normcase("/Home/User/.AWS")

    def test_case_variant_of_blocked_dir_rejected_when_case_insensitive(
        self, tmp_path, monkeypatch
    ):
        """A differently cased path cannot be used to reach a blocked directory."""
        blocked = tmp_path / "secrets"
        blocked.mkdir()
        monkeypatch.setattr(path_validation, "BLOCKED_DIRS", (os.path.realpath(str(blocked)),))
        monkeypatch.setattr(path_validation, "_CASE_INSENSITIVE_FS", True)

        with pytest.raises(ValueError):
            validate_path(str(tmp_path / "SECRETS"))

    def test_documented_casing_rejected_on_every_platform(self, monkeypatch):
        """The blocklist casing itself is rejected regardless of platform."""
        for case_insensitive in (True, False):
            monkeypatch.setattr(path_validation, "_CASE_INSENSITIVE_FS", case_insensitive)
            with pytest.raises(ValueError):
                validate_path(os.path.join(HOME, ".aws"))
