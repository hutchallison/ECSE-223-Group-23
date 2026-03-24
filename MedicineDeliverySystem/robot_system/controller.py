from navigator import Navigator
from config import Config

class Controller:
    def __init__(self):
        self.nav = Navigator(gyro=True)
    
    def collect_medicine(self):
        # Code to navigate to the medicine location and collect it
        self.nav.move_forward(Config.Controller.S1_SEGMENT1)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.S1_SEGMENT2)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.S1_SEGMENT3)
        self.nav.move_backward(Config.Controller.S1_SEGMENT3)

    def go_to_room1(self):
        self.nav.turn(90)
        self.nav.move_backward(Config.Controller.S1_SEGMENT1)
        self.nav.diff_turn(90, "right")
        self.nav.move_forward(Config.Controller.S1_SEGMENT2)

    def sweep_room1(self):
        # Code to sweep room 1 for obstacles
        self.nav.move_forward(Config.Controller.ROOM_SWEEP_LENGTH)
        self.nav.move_backward(Config.Controller.ROOM_SWEEP_LENGTH)
        self.nav.diff_turn(90, "left")
        self.nav.move_forward(Config.Controller.SWEEP_DIFF)
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.ROOM_SWEEP_LENGTH)
        self.nav.move_backward(Config.Controller.ROOM_SWEEP_LENGTH)
        self.nav.turn(90)
        self.nav.move_forward(Config.Controller.SWEEP_DIFF)
        self.nav.turn(-90)
        self.nav.move_forward(Config.Controller.ROOM_SWEEP_LENGTH)
        self.nav.move_backward(Config.Controller.ROOM_SWEEP_LENGTH)

if __name__ == "__main__":
    controller = Controller()
    controller.collect_medicine()
    controller.go_to_room1()
    controller.sweep_room1()

    