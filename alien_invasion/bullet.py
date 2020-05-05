import pygame
from pygame.sprite import Sprite

class Bullet(Sprite):
    """A class to manage bullets fired from the ship"""

    def __init__(self, ai_game):
        """Create the bullet object at the ship current position"""
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.color = self.settings.bullet_color

        #Create the rectangle of the bullet
        self.rect = pygame.Rect(0, 0, self.settings.bullet_width, self.settings.bullet_height)
        self.rect.midtop = ai_game.ship.rect.midtop

        #Position on the bullet into decimal
        self.y = float(self.rect.y)

    def update(self):
        """Move the bullet up the screen"""

        #update the decimal position
        self.y -= self.settings.bullet_speed
        self.rect.y = self.y

    def draw_bullet(self):
        """Draw the bullet on the screen"""
        pygame.draw.rect(self.screen,self.color,self.rect)






