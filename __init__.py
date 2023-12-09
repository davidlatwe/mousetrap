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
    "description": "Trap your mouse in a text input area.",
    "location": "Text Editor > Header",
    "doc_url": "https://github.com/davidlatwe/mousetrap",
    "tracker_url": "https://github.com/davidlatwe/mousetrap/issues",
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
    bl_options = {"REGISTER"}

    trapping = False
    activated = False
    handler = {}
    psize = 0

    def invoke(self, context, event):
        cls = self.__class__
        if cls.activated:
            cls.trapping = False
            cls.activated = False
            cls.guide_remove()
            print("Mouse Trap: Off")
            _redraw_headers(context)
            return {"FINISHED"}
        else:
            return self.execute(context)

    def execute(self, context):
        pref = context.preferences
        cls = self.__class__
        cls.psize = pref.ui_styles[0].widget_label.points
        cls.psize *= pref.system.ui_scale
        cls.trapping = True
        cls.activated = True
        cls.guide_install()
        print("Mouse Trap: On")
        _redraw_headers(context)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def trap(self, context, event):
        cls = self.__class__
        on_area = None
        mouse = (event.mouse_x, event.mouse_y)
        for area in context.screen.areas:
            if area.type not in {"CONSOLE", "TEXT_EDITOR"}:
                continue
            if _on(area, *mouse):
                for reg in area.regions:
                    if reg.type == "HEADER" and not _on(reg, *mouse):
                        on_area = area
                        break
                break
        if on_area:
            cls.trapping = True
            cls.activated = False

            def new_trap():
                if cls.trapping:
                    return 0.1
                with context.temp_override(area=on_area):
                    bpy.ops.mousetrap.activate("EXEC_DEFAULT")

            bpy.app.timers.register(new_trap)

    def modal(self, context, event):
        cls = self.__class__
        area = context.area

        if area.type not in {"CONSOLE", "TEXT_EDITOR"}:
            return {"PASS_THROUGH"}

        if not cls.activated:
            cls.trapping = False
            print("Mouse Trap: Off")
            return {"FINISHED"}

        if (event.type == "ESC" or
                (event.type == "RIGHTMOUSE" and event.value == "PRESS")):
            cls.trapping = False
            _redraw_headers(context)
            return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if not cls.trapping:
                self.trap(context, event)
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
            if event.type == "UP_ARROW" and event.value == "PRESS":
                center = space.top + (space.visible_lines // 2) - 3
                bpy.ops.text.scroll(lines=-1)
                bpy.ops.text.jump(line=center)
                return {"RUNNING_MODAL"}

            elif event.type == "DOWN_ARROW" and event.value == "PRESS":
                center = space.top + (space.visible_lines // 2) + 3
                bpy.ops.text.scroll(lines=1)  # TODO: This crash blender after
                bpy.ops.text.jump(line=center)
                return {"RUNNING_MODAL"}

        elif text and event.type == "HOME" and event.value == "PRESS":
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

        return {"PASS_THROUGH"}

    @classmethod
    def guide_install(cls):
        if "_" in cls.handler:
            return
        cls.handler["_"] = bpy.types.SpaceTextEditor.draw_handler_add(
            draw_79, (), "WINDOW", "POST_PIXEL"
        )

    @classmethod
    def guide_remove(cls):
        if "_" not in cls.handler:
            return
        bpy.types.SpaceTextEditor.draw_handler_remove(
            cls.handler.pop("_"), "WINDOW"
        )


def header_draw(self, context):
    cls = MOUSETRAP_OT_activate
    self.layout.separator()
    self.layout.operator(
        cls.bl_idname,
        text="",
        icon="MOUSE_RMB_DRAG" if cls.trapping else "MOUSE_MOVE",
        depress=cls.activated,
    )


_limit = "X" * 80  # around here


def draw_79():
    cls = MOUSETRAP_OT_activate
    area = bpy.context.area
    print(area.type)
    space = area.spaces.active
    blf.size(0, cls.psize)
    p, _ = blf.dimensions(0, _limit)

    w = 1
    h = area.height

    vertices = ((p, 0), (p + w, 0), (p, h), (p + w, h))
    indices = ((0, 1, 2), (2, 1, 3))
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "TRIS", {"pos": vertices}, indices=indices)
    shader.uniform_float("color", (1, 1, 1, 0.5))
    batch.draw(shader)


def register():
    bpy.utils.register_class(MOUSETRAP_OT_activate)
    bpy.types.TEXT_HT_header.append(header_draw)
    bpy.types.CONSOLE_HT_header.append(header_draw)


def unregister():
    bpy.types.CONSOLE_HT_header.remove(header_draw)
    bpy.types.TEXT_HT_header.remove(header_draw)
    bpy.utils.unregister_class(MOUSETRAP_OT_activate)


def reload():  # bpy.utils.text_editor_addon_reload()
    # Identifier of the script to reload
    #   this uses current text name
    #    change to your addon name
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
