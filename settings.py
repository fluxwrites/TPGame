player_radius = 20
player_color = (0, 0, 255)
goal_radius = 30
goal_color = (0, 255, 0)
screen_width = 640
screen_height = 480
distance_min = 50
distance_max = 150

assert (distance_max + player_radius + goal_radius) <= (screen_width / 2)
assert (distance_max + player_radius + goal_radius) <= (screen_height / 2)
