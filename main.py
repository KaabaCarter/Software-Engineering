"""Entry point used by the web build (pygbag). You can also run: python main.py"""
import asyncio

import pygame  # noqa: F401  (pygbag looks for this import to load pygame in the browser)

import wizard_duel

asyncio.run(wizard_duel.main())
