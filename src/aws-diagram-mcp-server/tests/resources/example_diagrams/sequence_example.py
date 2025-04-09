"""Example sequence diagram for testing."""

from diagrams import Diagram
from diagrams.programming.flowchart import Action, Decision, InputOutput, StartEnd


with Diagram('Sequence Example', show=False):
    user = StartEnd('User')
    login = InputOutput('Login Form')
    auth = Decision('Authenticated?')
    success = Action('Access Granted')
    failure = Action('Access Denied')

    user >> login >> auth
    auth >> success
    auth >> failure
