import threading
import time

# Weighted round-robin weights for lanes
lane_weights = [6, 4, 5, 7]  # Adjust as necessary
current_lane = 0  # Tracks the current lane being served
current_weight = lane_weights[current_lane]  # Tracks remaining weight for the current lane


path_locks = {
    dir: {
        "lock": threading.Lock(),
        "north": 0, "south": 0, "east": 0, "west": 0, "emergency_vehicle": 0
    }
    for dir in ["north", "east", "south", "west"]
}


lane_map = ["north", "east", "south", "west"]
route_map = {
    ("north", "straight"): "south",
    ("north", "left"): "east",
    ("north", "right"): "west",
    
    ("east", "straight"): "west",
    ("east", "left"): "south",
    ("east", "right"): "north",
    
    ("south", "straight"): "north",
    ("south", "left"): "west",
    ("south", "right"): "east",
    
    ("west", "straight"): "east",
    ("west", "left"): "north",
    ("west", "right"): "south",
}

timer_for_routes = {
    "north": {"time_of_start": None, "isActive": False},
    "east": {"time_of_start": None, "isActive": False},
    "south": {"time_of_start": None, "isActive": False},
    "west": {"time_of_start": None, "isActive": False}
}
def get_next_lane():
    """
    Determine the next lane to be served based on the weighted round-robin logic.
    - Update the global variables `current_lane` and `current_weight`.
    - Ensure that heavier traffic lanes are served more often.
    """
    global current_lane, current_weight 
    current_time = time.time()
    current_direction = lane_map[current_lane]
    route = timer_for_routes[current_direction]
    activation = route["isActive"]

    if not activation:
        route.update({"time_of_start": current_time, "isActive": True})

    if (current_time - route["time_of_start"]) >= current_weight:
        # Reset the timer for the current lane
        route.update({"time_of_start": None, "isActive": False})

        # Switch to the next lane in a round-robin manner
        current_lane = (current_lane + 1) % len(lane_map)
        current_weight = lane_weights[current_lane]  # Update weight
        next_direction = lane_map[current_lane]

        # Activate and start the timer for the new lane
        timer_for_routes[next_direction].update({"time_of_start": current_time, "isActive": True})
        print(f"Switched to lane {current_lane} ({next_direction}) with quantum of {current_weight} seconds")

    return current_lane



def can_enter_intersection(vehicle):
    """
    Check if the vehicle's route conflicts with any currently locked paths.
    - Return True if the vehicle can safely enter the intersection.
    """
    start_dir = lane_map[vehicle.lane]
    end_dir = route_map[(start_dir, vehicle.route)] 
    vehicle_id = vehicle.vehicle_id

    # Check if it's the vehicle's turn
    if not is_lane_turn(vehicle, end_dir):
        print(f"Vehicle {vehicle_id} is waiting - lane {vehicle.lane} does not have the right of way.")
        return False  

    # Emergency vehicles take priority
    if vehicle.vehicle_type == "Regular" and path_locks[end_dir]["emergency_vehicle"] > 0:
        print(f"Vehicle {vehicle_id} must wait - emergency vehicle present at {end_dir}.")
        return False

    # Check if the path is open from the start direction
    if path_locks[end_dir][start_dir] > 0:
        print(f"Vehicle {vehicle_id} can proceed - {start_dir} to {end_dir} is open.")
        return True

    # Check if the intersection path is locked
    if path_locks[end_dir]["lock"].locked():
        print(f"Vehicle {vehicle_id} is blocked - path {start_dir} → {end_dir} is locked.")
        return False

    return True



def enter_intersection(vehicle):
    """
    Lock the specific path for the vehicle, preventing conflicts with other vehicles.
    """
    start, end = lane_map[vehicle.lane], route_map[(lane_map[vehicle.lane], vehicle.route)]
    lock_of_route = path_locks[end]["lock"]

    with threading.Lock():
        path_locks[end][start] += 1
        if path_locks[end][start] == 1:
            lock_of_route.acquire()


def exit_intersection(vehicle):
    """
    Release the lock for the vehicle's path, allowing other vehicles to proceed.
    """
    start, end = lane_map[vehicle.lane], route_map[(lane_map[vehicle.lane], vehicle.route)]
    lock_of_route = path_locks[end]["lock"]
    with threading.Lock():
        path_locks[end][start] -= 1
        if path_locks[end][start] == 0:
            lock_of_route.release()


def is_lane_turn(vehicle , end_direction):
    """
    Check if it is the given lane's turn to serve vehicles based on round-robin scheduling.
    """
    return end_direction == lane_map[current_lane]


# Vehicle Class is already provided
class Vehicle(threading.Thread):
    def __init__(self, vehicle_id, vehicle_type, lane, route, crossing_time):
        threading.Thread.__init__(self)
        self.vehicle_id = vehicle_id  # Unique ID for the vehicle
        self.vehicle_type = vehicle_type  # "Regular" or "Emergency"
        self.lane = lane  # Lane of the vehicle (0-3)
        self.route = route  # "straight", "left", or "right"
        self.crossing_time = crossing_time  # Time to cross the intersection

    def run(self):
        """
        Integrate the synchronization logic for vehicles here.
        Use the provided functions to ensure collision-free and fair operations.
        """
        start, end = lane_map[self.lane], route_map[(lane_map[self.lane], self.route)] 

        if self.vehicle_type == "Emergency":
            path_locks[end]["emergency_vehicle"] += 1

        while not can_enter_intersection(self):
            get_next_lane()  # Ensures round-robin lane switching
            #print(f"Vehicle {self.vehicle_id} is waiting - access restricted.")
            time.sleep(3)

        if self.vehicle_type == "Emergency":
            path_locks[end]["emergency_vehicle"] -= 1

        enter_intersection(self)
        print(f"Vehicle {self.vehicle_id} entering intersection...")
        time.sleep(self.crossing_time)
        exit_intersection(self)
        print(f"Vehicle {self.vehicle_id} exited intersection.")

vehicles = [
    {"vehicle_id": 1, "vehicle_type": "Regular", "lane": 0, "route": "straight", "crossing_time": 2},
    {"vehicle_id": 2, "vehicle_type": "Emergency", "lane": 1, "route": "right", "crossing_time": 1},
    {"vehicle_id": 3, "vehicle_type": "Regular", "lane": 2, "route": "left", "crossing_time": 3},
    {"vehicle_id": 4, "vehicle_type": "Regular", "lane": 3, "route": "straight", "crossing_time": 2},
    {"vehicle_id": 5, "vehicle_type": "Regular", "lane": 0, "route": "right", "crossing_time": 1},
    {"vehicle_id": 6, "vehicle_type": "Emergency", "lane": 1, "route": "straight", "crossing_time": 2},
]

def create_vehicles():
    vehicle_threads = []
    for v in vehicles:
        vehicle = Vehicle(
            vehicle_id=v["vehicle_id"],
            vehicle_type=v["vehicle_type"],
            lane=v["lane"],
            route=v["route"],
            crossing_time=v["crossing_time"]
        )
        vehicle_threads.append(vehicle)
        vehicle.start()
    return vehicle_threads

vehicle_threads = create_vehicles()
for vehicle in vehicle_threads:
    vehicle.join()

print("Tasks Done Correctly")