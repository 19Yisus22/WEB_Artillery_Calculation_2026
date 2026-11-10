# /// script
# dependencies = [
#   "pygame-ce",
# ]
# ///
import asyncio

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from artillery_calculation import main

asyncio.run(main())