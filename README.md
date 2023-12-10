<h1 align=center>mousetrap</h1>
<p align=center><i>Trap your mouse in blender text input area, stay focused.</i></p>
<p align=center><img src="https://github.com/davidlatwe/mousetrap/assets/3357009/c87aaa0a-3dc5-4608-8739-0a7b79f9f085"></p>

### Why?

Blender's text editor and console lose keyboard input focus when mouse cursor is not hovering on those areas. While
other graphical interface like search bar or name input field does hold. It's unfair!

### Usage

1. Once installed, a mouse-move icon button should appear at right side of console and text editor header.

    <img width="420" alt="image" src="https://github.com/davidlatwe/mousetrap/assets/3357009/43fdded8-a175-40eb-942d-ede72c65d65d">

2. Keymap `Ctrl` + `Shift` + `` ` `` is added for fast activation, or you can just toggle that button.
3. Once activated, your mouse is trapped inside that panel with your keyboard input focus.
4. You can right click to temporary leave the trapping area and move somewhere else, and left click on trapping area to 
   regain focus.
5. Press `Esc` to deactivate completely.

### Bonus

* When mousetrap is on, press `Home` key moves cursor to the first character in line, instead of line start.
* `Ctrl` + `Up`/`Down` to scroll with cursor (Disabled due to this can cause Blender to crash if the focus was shifted 
  to other application and back.)
