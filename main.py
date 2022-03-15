import asyncio
import random
from asyncio import sleep

from graphics import *

## Exercise variables
NUM_A_WEIGHT = 0.6
NUM_B_WEIGHT = 1
TIME_A_WEIGHT = 0.4
TIME_B_WEIGHT = 0.85

MIN_TIME_BETWEEN_SWITCHES = 4

SPAWN_PROBABILITY_PER_STEP = 0.82

#####################

WINDOW_WIDTH = 1500
WINDOW_HEIGHT = 800
CAR_SIZE = 40
CAR_UNDRAW_TIME = 8
MOVE_OFFSET = 5
MOVE_SPEED = CAR_SIZE + MOVE_OFFSET
UPDATE_DELAY = 0.2
STEPS_TO_SWITCH = 5

def draw_horizontal_dotted_line(window, x_start, x_end, y, dot_length):
    for x in range(x_start, x_end, dot_length*2):
        line = Line(Point(x, y), Point(x + dot_length, y))
        line.draw(window)

def draw_vertical_dotted_line(window, y_start, y_end, x, dot_length):
    for y in range(y_start, y_end, dot_length*2):
        line = Line(Point(x, y), Point(x, y + dot_length))
        line.draw(window)

def draw_roads(window):
    road_line_points = [
        [Point(0, 50), Point(WINDOW_WIDTH, 50)],
        [Point(0, 300), Point(650, 300)],
        [Point(850, 300), Point(WINDOW_WIDTH, 300)],
        [Point(650, 300), Point(650, WINDOW_HEIGHT)],
        [Point(850, 300), Point(850, WINDOW_HEIGHT)]
    ]

    for points in road_line_points:
        line = Line(points[0], points[1])
        line.draw(window)

    draw_horizontal_dotted_line(window, 0, WINDOW_WIDTH, 113, 30)
    draw_horizontal_dotted_line(window, 0, WINDOW_WIDTH, 175, 50)
    draw_horizontal_dotted_line(window, 0, WINDOW_WIDTH, 238, 30)
    draw_vertical_dotted_line(window, 300, WINDOW_HEIGHT, 750, 50)

def drawText(window, anchorPoint):
    text_object = Text(anchorPoint, "")
    text_object.draw(window)
    return text_object

def create_car(x, y):
    car = Rectangle(Point(x - CAR_SIZE/2, y - CAR_SIZE/2), Point(x + CAR_SIZE/2, y + CAR_SIZE/2))
    car.setFill("green")
    return car

def spawn_random_car(lanes):
    lane_number = random.randrange(len(lanes))
    lane = lanes[lane_number]
    car = create_car(lane[0], lane[1])
    return car, lane_number

def detect_collision_and_fix(car, previous_car, move_direction):
    if previous_car:
        car_p1 = car.getP1()
        previous_car_p1 = previous_car.getP1()
        if move_direction == -1:
            if car_p1.getX() < previous_car_p1.getX() + CAR_SIZE:
                car.move(previous_car_p1.getX() + CAR_SIZE + MOVE_OFFSET - car_p1.getX(), 0)
        elif move_direction == 0:
            if car_p1.getY() < previous_car_p1.getY() + CAR_SIZE:
                car.move(0, previous_car_p1.getY() + CAR_SIZE + MOVE_OFFSET - car_p1.getY())
        elif move_direction == 1:
            if car_p1.getX() + CAR_SIZE > previous_car_p1.getX():
                car.move(previous_car_p1.getX() - car_p1.getX() - CAR_SIZE - MOVE_OFFSET, 0)

def is_over_light(car, light_coordinate, move_direction):
    car_p1 = car.getP1()
    if move_direction == -1:
        return car_p1.getX() < light_coordinate
    elif move_direction == 0:
        return car_p1.getY() < light_coordinate
    elif move_direction == 1:
        return car_p1.getX() + CAR_SIZE > light_coordinate

def step_car(car, light_coordinate, move_direction, X, ignore_red_light, hold_all = False):
    dx = move_direction
    dy = -1 if move_direction == 0 else 0
    
    car.move(dx * MOVE_SPEED, dy * MOVE_SPEED)
    
    # check and correct if over a red light
    if not ignore_red_light and is_over_light(car, light_coordinate, move_direction):
        car_p1 = car.getP1()
        if move_direction == -1 and (X != 1 or hold_all):
            car.move(light_coordinate - car_p1.getX(), 0)
        elif move_direction == 0 and (X != 0 or hold_all):
            car.move(0, light_coordinate - car_p1.getY())
        elif move_direction == 1 and (X != 1 or hold_all):
            car.move(light_coordinate - car_p1.getX() - CAR_SIZE, 0)

def calculate_car_list_detection_time(car_list):
    sum = 0
    current_time = time.time()
    for car_item in car_list:
        sum += current_time - car_item[1]
    return sum

async def async_remove_car_from_list(list, car_item):
    await sleep(CAR_UNDRAW_TIME)
    if car_item in list:
        list.remove(car_item)
        car_item[0].undraw()

async def main():
    window = GraphWin("Traffic Light Simulation", WINDOW_WIDTH, WINDOW_HEIGHT)

    draw_roads(window)

    drawText(window, Point(40, 350)).setText("num_A")
    drawText(window, Point(40, 370)).setText("num_B")
    drawText(window, Point(40, 390)).setText("time_A")
    drawText(window, Point(40, 410)).setText("time_B")
    drawText(window, Point(100, 460)).setText("A weighted total")
    drawText(window, Point(100, 480)).setText("B weighted total")
    num_A_text = drawText(window, Point(100, 350))
    num_B_text = drawText(window, Point(100, 370))
    time_A_text = drawText(window, Point(100, 390))
    time_B_text = drawText(window, Point(100, 410))
    A_weighted_total_text = drawText(window, Point(200, 460))
    B_weighted_total_text = drawText(window, Point(200, 480))

    # [x, y, light_coordinate, move_direction]
    # x and y define the start of the lane
    # coordinate of lights in the respective axis
    # move_direction defines the lane's direction
    #       -1 = left
    #       0 = up
    #       1 = right
    lanes = [
        [WINDOW_WIDTH, 81.5, 850, -1],
        [WINDOW_WIDTH, 144, 850, -1],
        [0, 206.5, 650, 1],
        [0, 269, 650, 1],
        [800, WINDOW_HEIGHT, 300, 0]
    ]

    # list of cars for each lane in the form of [car_shape_object, timestamp_of_detection]
    car_lists = {}
    # list for cars that have passed the lights
    cars_over_lights = []

    for index, _ in enumerate(lanes):
        car_lists[index] = []


    X = 1
    previous_step_X = X
    steps_since_last_switch = 0
    hold_all = False
    last_switch_timestamp = time.time()

    while True:
        if (random.randint(0, 1000)/1000 < SPAWN_PROBABILITY_PER_STEP):
            car, lane_number = spawn_random_car(lanes)
            car.draw(window)
            car_lists[lane_number].append([car, time.time()])

        num_A_east = len(car_lists[0]) + len(car_lists[1])
        num_A_west = len(car_lists[2]) + len(car_lists[3])
        num_A = num_A_east + num_A_west
        num_B = len(car_lists[4])

        time_A_east = calculate_car_list_detection_time(car_lists[0]) + calculate_car_list_detection_time(car_lists[1])
        time_A_west = calculate_car_list_detection_time(car_lists[2]) + calculate_car_list_detection_time(car_lists[3])
        time_A = time_A_east + time_A_west
        time_B = calculate_car_list_detection_time(car_lists[4])

        ####################################
        ## Actual exercise algorithm

        if time.time() - last_switch_timestamp >= MIN_TIME_BETWEEN_SWITCHES:
            if not hold_all:
                if NUM_A_WEIGHT * num_A + TIME_A_WEIGHT * time_A > NUM_B_WEIGHT * num_B + TIME_B_WEIGHT * time_B:
                    X = 1
                else:
                    X = 0

                if X != previous_step_X:
                    previous_step_X = X
                    hold_all = True
                    last_switch_timestamp = time.time()

        if hold_all and steps_since_last_switch <= STEPS_TO_SWITCH:
            steps_since_last_switch += 1
        else:
            steps_since_last_switch = 0
            hold_all = False

        #####################################
        
        num_A_text.setText(f'{num_A}')
        num_B_text.setText(f'{num_B}')
        time_A_text.setText(f'{int(time_A)}')
        time_B_text.setText(f'{int(time_B)}')
        A_weighted_total_text.setText('{:.4f}'.format(NUM_A_WEIGHT * num_A + TIME_A_WEIGHT * time_A))
        B_weighted_total_text.setText('{:.4f}'.format(NUM_B_WEIGHT * num_B + TIME_B_WEIGHT * time_B))

        for index, car_list in car_lists.items():
            for car_index, car_item in enumerate(car_list):
                car = car_item[0]
                previous_car = None if car_index == 0 else car_list[car_index - 1][0]
                light_coordinate = lanes[index][2]
                move_direction = lanes[index][3]
                step_car(car, light_coordinate, move_direction, X, False, hold_all)
                detect_collision_and_fix(car, previous_car, move_direction)

                if is_over_light(car, light_coordinate, move_direction):
                    car.setFill("red")
                    car_list.remove(car_item)
                    over_lights_item = [car, move_direction]
                    cars_over_lights.append(over_lights_item)
                    asyncio.gather(async_remove_car_from_list(cars_over_lights, over_lights_item))
                    
        for car_item in cars_over_lights:
            step_car(car_item[0], None, car_item[1], None, True)

        await sleep(UPDATE_DELAY)

asyncio.run(main())
