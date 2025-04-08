"""Example flow diagram for testing."""

from diagrams import Diagram
from diagrams.programming.flowchart import Action, Decision, Delay, InputOutput, StartEnd


with Diagram('Flow Example', show=False):
    start = StartEnd('Start')
    order = InputOutput('Order Received')
    check = Decision('In Stock?')
    process = Action('Process Order')
    wait = Delay('Backorder')
    ship = Action('Ship Order')
    end = StartEnd('End')

    start >> order >> check
    check >> process >> ship >> end
    check >> wait >> process
