import matplotlib.pyplot as plt
import numpy as np
# from fast_perlin_noise import PerlinNoise
import noise

# noise_generator: PerlinNoise = PerlinNoise(width=256, height=256)
# noise_image: np.ndarray = noise_generator.generate_noise_matrix()
# plt.imshow(noise_image)

def make_perlin_noise(x: int,
                      y: int,
                      shape: tuple,
                      scale: float,
                      octaves: int,
                      persistence: float,
                      lacunarity: float,
                      base: int):
    result = noise.pnoise2(x / scale,
                           y / scale,
                           octaves=octaves,
                           persistence=persistence,
                           lacunarity=lacunarity,
                           repeatx=shape[0],
                           repeaty=shape[1],
                           base=base)
    return result

def main():
    shape = (1024, 1024)
    scale = 50.0
    octaves = 4
    persistence = 0.5
    lacunarity = 2.0
    # base = random.randint(1, 1024)
    base = 8
    world = np.zeros(shape)
    for i in range(shape[0]):
        for j in range(shape[1]):
            world[i][j] = make_perlin_noise(i, j, shape, scale, octaves, persistence, lacunarity, base)
    world = np.maximum(world, 0)
    world[world != 0] = 1
    world = world * 255
    world = world.astype(np.uint8)
    im = Image.fromarray(world)
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.show()


if __name__ == "__main__":
    main()
