import sys
import bpy  # noqa
import blf  # noqa
import gpu  # noqa
from gpu_extras.batch import batch_for_shader  # noqa

bl_info = {
    "name": "mousetrap",
    "version": (0, 1, 0),
    "blender": (3, 4, 0),
    "category": "Interface",
    "author": "David Lai",
    "location": "Text Editor > Header",
    "doc_url": "https://github.com/davidlatwe/mousetrap",
    "tracker_url": "https://github.com/davidlatwe/mousetrap/issues",
    "description": "Trap your mouse in a text input area.",
}


def _on(zone, x, y):
    return (zone.x < x < (zone.x + zone.width) and
            zone.y < y < (zone.y + zone.height))


def _redraw_headers(context):
    for area in context.screen.areas:
        if area.type in {"CONSOLE", "TEXT_EDITOR"}:
            area.tag_redraw()


class MOUSETRAP_OT_activate(bpy.types.Operator):
    bl_idname = "mousetrap.activate"
    bl_label = "Activate Mouse Trap"
    bl_description = "Trap your mouse in a text input area"
    bl_options = {"INTERNAL"}

    # global flags
    trapping = False
    activated = False

    def _deactivate(self, context):
        cls = self.__class__
        cls.trapping = False
        cls.activated = False
        _redraw_headers(context)
        self.report({"OPERATOR"}, "mousetrap: off")

    def invoke(self, context, _event):
        cls = self.__class__
        if cls.activated:
            self._deactivate(context)
            return {"FINISHED"}
        else:
            return self.execute(context)

    def execute(self, context):
        cls = self.__class__
        cls.trapping = True
        cls.activated = True
        _redraw_headers(context)
        self.report({"OPERATOR"}, "mousetrap: on")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        cls = self.__class__
        area = context.area

        if area.type not in {"CONSOLE", "TEXT_EDITOR"}:
            return {"PASS_THROUGH"}

        if not cls.activated:
            cls.trapping = False
            self.report({"OPERATOR"}, "mousetrap: starting new trap...")
            return {"FINISHED"}

        if event.type == "ESC":
            self._deactivate(context)
            return {"FINISHED"}

        if event.type == "RIGHTMOUSE" and event.value == "PRESS":
            # take a break
            if cls.trapping:
                cls.trapping = False
                _redraw_headers(context)
                return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if not cls.trapping:
                self._trap_on_pressed(context, event)
                return {"PASS_THROUGH"}

        space = area.spaces.active
        text = getattr(space, "text", None)

        if cls.trapping:
            min_x = area.x
            max_x = area.x + area.width
            min_y = area.y
            max_y = area.y + area.height
            pad = 4

            for region in context.area.regions:
                if region.type == "HEADER":
                    max_y -= region.height
                if region.type == "FOOTER":
                    min_y += region.height
                if region.type == "UI":
                    max_x -= region.width

            if event.mouse_x < min_x:
                context.window.cursor_warp(min_x + pad, event.mouse_y)
            if event.mouse_x > max_x:
                context.window.cursor_warp(max_x - pad, event.mouse_y)
            if event.mouse_y < min_y:
                context.window.cursor_warp(event.mouse_x, min_y + pad)
            if event.mouse_y > max_y:
                context.window.cursor_warp(event.mouse_x, max_y - pad)

        # convenient stuff
        #
        if text and event.ctrl and not (event.shift or event.alt):
            return self._scroll(event)
        elif text and event.type == "HOME" and event.value == "PRESS":
            return self._char_home(text, event)

        return {"PASS_THROUGH"}

    @classmethod
    def _trap_on_pressed(cls, context, event):
        mouse = (event.mouse_x, event.mouse_y)
        trap_area = None
        for area in context.screen.areas:
            if area.type not in {"CONSOLE", "TEXT_EDITOR"}:
                continue
            if _on(area, *mouse):
                for region in area.regions:
                    # Do nothing if mouse is on Header, for toggling button.
                    if region.type == "HEADER" and not _on(region, *mouse):
                        trap_area = area
                        break
                break

        if trap_area:
            cls._restart(context, trap_area)

    @classmethod
    def _restart(cls, context, trap_area):
        cls.trapping = True  # For new trap to wait.
        cls.activated = False

        def new_trap():
            if cls.trapping:
                return 0.1
            with context.temp_override(area=trap_area):
                bpy.ops.mousetrap.activate("EXEC_DEFAULT")

        bpy.app.timers.register(new_trap)

    def _scroll(self, event):
        _safe = False
        # Why unsafe? Here are the steps to crash:
        # 1. Activate mousetrap
        # 2. Right click release mouse
        # 3. Click another window e.g. web browser, and back to blender
        # 4. Hit Ctrl + Up/Down in Text Editor, blender crashed
        if _safe:
            if event.type == "UP_ARROW" and event.value == "PRESS":
                bpy.ops.mousetrap.scroll(step=-1)
                return {"RUNNING_MODAL"}

            elif event.type == "DOWN_ARROW" and event.value == "PRESS":
                bpy.ops.mousetrap.scroll(step=1)
                return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    def _char_home(self, text, event):
        line = text.current_line.body
        home = len(line) - len(line.lstrip())
        if text.current_character == home:
            home = 0
        elif text.select_end_character == home:
            home = 0
        text.cursor_set(
            line=text.current_line_index,
            character=home,
            select=event.shift,
        )
        return {"RUNNING_MODAL"}


class MOUSETRAP_OT_scroll(bpy.types.Operator):
    bl_idname = "mousetrap.scroll"
    bl_label = "Trap scroll"
    bl_description = "Scroll while holding cursor at view center"
    bl_options = {"INTERNAL"}

    step: bpy.props.IntProperty()

    def execute(self, context):
        space = context.area.spaces.active
        center = space.top + (space.visible_lines // 2) + (3 * self.step)
        bpy.ops.text.jump(line=center)
        bpy.ops.text.scroll(lines=self.step)
        return {"FINISHED"}


def _header_draw(self, _context):
    cls = MOUSETRAP_OT_activate
    self.layout.separator()
    self.layout.operator(
        cls.bl_idname,
        text="",
        icon="MOUSE_RMB_DRAG" if cls.trapping else "MOUSE_MOVE",
        depress=cls.activated,
    )


def register():
    bpy.utils.register_class(MOUSETRAP_OT_scroll)
    bpy.utils.register_class(MOUSETRAP_OT_activate)
    bpy.types.TEXT_HT_header.append(_header_draw)
    bpy.types.CONSOLE_HT_header.append(_header_draw)


def unregister():
    bpy.types.CONSOLE_HT_header.remove(_header_draw)
    bpy.types.TEXT_HT_header.remove(_header_draw)
    bpy.utils.unregister_class(MOUSETRAP_OT_activate)
    bpy.utils.unregister_class(MOUSETRAP_OT_scroll)


def reload():
    # This can be `bpy.utils.text_editor_addon_reload()`?

    # Identifier of the script to reload
    #   You can use current text name (__file__, but may not work if renamed),
    #   or use your addon name.
    key = __file__

    # Setup registry
    if not hasattr(sys, "_my_scripts"):
        sys._my_scripts = {}
    registry = sys._my_scripts

    # Unregister previous session
    prev_globals = registry.pop(key, None)
    if prev_globals:
        eval("unregister()", prev_globals)

    # Register and save session
    register()
    registry[key] = globals()


if __name__ == "__main__":
    reload()
