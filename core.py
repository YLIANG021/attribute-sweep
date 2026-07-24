import bpy
from bpy.app.translations import pgettext_iface as iface_
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Mesh, Object, Operator, PropertyGroup, UIList

from .locales import TRANSLATIONS


REGISTERED_PANEL_CALLBACKS = []
DIALOG_WIDTH = 320
LIST_ROWS = 7
ATTRIBUTE_NAME_COLUMN_FACTOR = 0.5

ATTRIBUTE_DOMAIN_LABELS = {
    "POINT": "Vertex",
    "EDGE": "Edge",
    "FACE": "Face",
    "CORNER": "Face Corner",
    "CURVE": "Curve",
    "INSTANCE": "Instance",
    "LAYER": "Layer",
}

ATTRIBUTE_TYPE_LABELS = {
    "FLOAT": "Float",
    "INT": "Integer",
    "FLOAT_VECTOR": "Vector",
    "FLOAT_COLOR": "Float Color",
    "BYTE_COLOR": "Byte Color",
    "STRING": "String",
    "BOOLEAN": "Boolean",
    "FLOAT2": "2D Vector",
    "INT8": "8-bit Integer",
    "INT32_2D": "2D Integer Vector",
    "QUATERNION": "Quaternion",
    "FLOAT4X4": "Matrix",
}

def iter_selected_mesh_objects(context):
    """Yield selected objects with editable mesh data."""
    for obj in context.selected_objects:
        if obj.type != "MESH":
            continue
        data = getattr(obj, "data", None)
        attributes = getattr(data, "attributes", None)
        if data is None or attributes is None or data.library:
            continue
        yield obj


def mesh_users_by_pointer():
    users = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        users.setdefault(obj.data.as_pointer(), []).append(obj)
    return users


def get_inactive_attribute_index(_scene):
    return -1


def ignore_attribute_index_change(_scene, _value):
    pass


class GABD_PG_ObjectRef(PropertyGroup):
    object: PointerProperty(type=Object)


class GABD_PG_MeshRef(PropertyGroup):
    mesh: PointerProperty(type=Mesh)


class GABD_PG_AttributeItem(PropertyGroup):
    name: StringProperty()
    selected: BoolProperty(name="", default=False)
    meta_text: StringProperty(options={"SKIP_SAVE"})
    meta_tooltip: StringProperty(options={"SKIP_SAVE"})
    object_count: IntProperty(default=0, options={"SKIP_SAVE"})
    objects: CollectionProperty(type=GABD_PG_ObjectRef)
    meshes: CollectionProperty(type=GABD_PG_MeshRef)


def attribute_matches_search(item, search_text):
    search_text = search_text.strip().casefold()
    return not search_text or search_text in item.name.casefold()


def attribute_meta_label(domain, data_type):
    domain_label = ATTRIBUTE_DOMAIN_LABELS.get(domain, domain.replace("_", " ").title())
    type_label = ATTRIBUTE_TYPE_LABELS.get(data_type, data_type.replace("_", " ").title())
    return f"{iface_(domain_label)} · {iface_(type_label)}"


class GABD_OT_AttributeMetaInfo(Operator):
    bl_idname = "object.gabd_attribute_meta_info"
    bl_label = "Attribute Information"
    bl_options = {"INTERNAL"}

    attribute_index: IntProperty(options={"SKIP_SAVE"})

    @classmethod
    def description(cls, context, properties):
        items = context.window_manager.gabd_attribute_items
        if 0 <= properties.attribute_index < len(items):
            return items[properties.attribute_index].meta_tooltip
        return iface_("Attribute Information")

    def execute(self, context):
        return {"FINISHED"}


class GABD_OT_BulkSelect(Operator):
    bl_idname = "object.gabd_bulk_select_attributes"
    bl_label = "Batch Select Attributes"
    bl_options = {"INTERNAL"}

    action: EnumProperty(
        name="Selection Mode",
        items=(
            ("ALL", "Select All Results", "Select every attribute in the current search results"),
            ("CLEAR", "Clear All", "Clear every selected attribute"),
            ("INVERT", "Invert Results", "Invert attributes in the current search results"),
        ),
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        items = context.window_manager.gabd_attribute_items
        visible_items = [
            item
            for item in items
            if attribute_matches_search(item, context.window_manager.gabd_attribute_filter)
        ]

        if self.action == "CLEAR":
            for item in items:
                item.selected = False
        elif self.action == "ALL":
            for item in visible_items:
                item.selected = True
        elif self.action == "INVERT":
            for item in visible_items:
                item.selected = not item.selected

        return {"FINISHED"}


class GABD_OT_SelectAttributeObjects(Operator):
    bl_idname = "object.gabd_select_attribute_objects"
    bl_label = "Select Objects with Attribute"
    bl_description = "Select objects that contained this attribute at scan time without changing the deletion scope"
    bl_options = {"INTERNAL"}

    attribute_index: IntProperty(options={"SKIP_SAVE"})

    def execute(self, context):
        items = context.window_manager.gabd_attribute_items
        if not 0 <= self.attribute_index < len(items):
            self.report({"WARNING"}, iface_("The scan results are no longer valid; scan again"))
            return {"CANCELLED"}

        item = items[self.attribute_index]
        view_layer_objects = {
            obj.as_pointer(): obj
            for obj in context.view_layer.objects
        }
        for obj in context.selected_objects:
            obj.select_set(False)

        selected = []
        skipped = 0
        for object_ref in item.objects:
            obj = object_ref.object
            if obj is None:
                skipped += 1
                continue
            obj = view_layer_objects.get(obj.as_pointer())
            if obj is None or obj.hide_select or obj.hide_get(view_layer=context.view_layer):
                skipped += 1
                continue
            try:
                obj.select_set(True, view_layer=context.view_layer)
            except RuntimeError:
                skipped += 1
                continue
            selected.append(obj)

        if not selected:
            self.report({"WARNING"}, iface_("No matching selectable objects exist in the current view layer"))
            return {"CANCELLED"}

        context.view_layer.objects.active = selected[0]
        message = iface_('Selected {count} objects containing "{name}"').format(
            count=len(selected),
            name=item.name,
        )
        if skipped:
            message += iface_("; skipped {count} hidden or unselectable objects").format(
                count=skipped
            )
        self.report({"INFO"}, message)
        return {"FINISHED"}


class GABD_UL_AttributeNames(UIList):
    bl_idname = "GABD_UL_attribute_names"

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        search_text = context.window_manager.gabd_attribute_filter
        flags = [
            self.bitflag_filter_item if attribute_matches_search(item, search_text) else 0
            for item in items
        ]
        return flags, []

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        split = row.split(factor=ATTRIBUTE_NAME_COLUMN_FACTOR, align=True)
        name_column = split.row(align=True)
        name_column.prop(item, "selected", text="")
        name_column.label(text=item.name, translate=False)

        details = split.row(align=True)
        meta = details.row(align=True)
        meta.active = False
        meta_operator = meta.operator(
            GABD_OT_AttributeMetaInfo.bl_idname,
            text=item.meta_text,
            emboss=False,
        )
        meta_operator.attribute_index = index

        stats = details.row(align=True)
        stats.alignment = "RIGHT"
        stats.label(text=f"{item.object_count} Obj", translate=False)
        details.separator(factor=1.4)

        select_operator = details.operator(
            GABD_OT_SelectAttributeObjects.bl_idname,
            text="",
            icon="RESTRICT_SELECT_OFF",
            emboss=True,
        )
        select_operator.attribute_index = index


def clear_attribute_state(window_manager):
    window_manager.gabd_attribute_items.clear()
    window_manager.gabd_attribute_index = -1
    window_manager.gabd_attributes_fetched = False
    if hasattr(window_manager, "gabd_attribute_filter"):
        window_manager.gabd_attribute_filter = ""


def checked_deletion_impact(items):
    attribute_removals = 0
    meshes = {}
    for item in items:
        if not item.selected:
            continue
        for mesh_ref in item.meshes:
            mesh = mesh_ref.mesh
            if mesh is None:
                continue
            attribute_removals += 1
            meshes[mesh.as_pointer()] = mesh

    if not meshes:
        return 0, 0, False

    affected_objects = sum(
        1
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj.data is not None
        and obj.data.as_pointer() in meshes
    )
    return attribute_removals, affected_objects, affected_objects > len(meshes)


def update_fetch_attributes(operator, context):
    if not operator.fetch_requested:
        return

    items = context.window_manager.gabd_attribute_items
    items.clear()

    selected_objects = list(iter_selected_mesh_objects(context))
    mesh_objects = {}
    mesh_data = {}
    for obj in selected_objects:
        mesh_pointer = obj.data.as_pointer()
        mesh_data[mesh_pointer] = obj.data
        mesh_objects.setdefault(mesh_pointer, []).append(obj)

    records = {}
    for mesh_pointer, data in mesh_data.items():
        for attribute in data.attributes:
            if attribute.is_internal or attribute.is_required:
                continue
            record = records.setdefault(
                attribute.name,
                {"meshes": {}, "objects": {}, "spec_meshes": {}},
            )
            record["meshes"][mesh_pointer] = data
            spec = (attribute.domain, attribute.data_type)
            record["spec_meshes"].setdefault(spec, {})[mesh_pointer] = data
            for obj in mesh_objects[mesh_pointer]:
                record["objects"][obj.as_pointer()] = obj

    all_mesh_users = mesh_users_by_pointer()

    for name in sorted(records, key=str.casefold):
        record = records[name]
        affected_objects = {}
        for mesh_pointer in record["meshes"]:
            for obj in all_mesh_users.get(mesh_pointer, ()):
                affected_objects[obj.as_pointer()] = obj

        item = items.add()
        item.name = name
        item.object_count = len(affected_objects)

        spec_details = []
        for spec, meshes in record["spec_meshes"].items():
            spec_objects = {}
            for mesh_pointer in meshes:
                for obj in all_mesh_users.get(mesh_pointer, ()):
                    spec_objects[obj.as_pointer()] = obj
            spec_details.append(
                (attribute_meta_label(*spec), len(spec_objects))
            )
        spec_details.sort(key=lambda detail: detail[0])

        if len(spec_details) == 1:
            item.meta_text = spec_details[0][0]
            item.meta_tooltip = iface_("Domain/Data Type: {meta}").format(
                meta=item.meta_text
            )
        else:
            item.meta_text = iface_("Domain/Type Mismatch")
            detail_lines = "\n".join(
                iface_("{label}: {count} Objects").format(label=label, count=count)
                for label, count in spec_details
            )
            item.meta_tooltip = (
                iface_("Meshes use different domains or data types for this attribute name")
                + "\n"
                f"{detail_lines}"
            )

        for obj in affected_objects.values():
            object_ref = item.objects.add()
            object_ref.object = obj
        for mesh in record["meshes"].values():
            mesh_ref = item.meshes.add()
            mesh_ref.mesh = mesh

    context.window_manager.gabd_attribute_index = -1
    context.window_manager.gabd_attributes_fetched = True

    operator.fetch_requested = False

    if not items:
        operator.report({"INFO"}, iface_("The selected meshes have no manageable geometry attributes"))


class GABD_OT_OpenManager(Operator):
    bl_idname = "object.attribute_sweep"
    bl_label = "Attribute Sweep"
    bl_description = "Scan selected meshes and remove geometry attributes in batches"
    bl_options = {"REGISTER", "UNDO"}

    fetch_requested: BoolProperty(
        name="Scan",
        default=False,
        options={"SKIP_SAVE"},
        update=update_fetch_attributes,
    )

    @classmethod
    def poll(cls, context):
        return any(True for _ in iter_selected_mesh_objects(context))

    def invoke(self, context, event):
        self.fetch_requested = False
        clear_attribute_state(context.window_manager)
        dialog_options = {"width": DIALOG_WIDTH}
        if bpy.app.version >= (4, 0, 0):
            dialog_options["confirm_text"] = iface_("Delete")
            object_count = sum(1 for _ in iter_selected_mesh_objects(context))
            dialog_options["title"] = iface_("Attribute Sweep ({count} Objects)").format(
                count=object_count
            )
        return context.window_manager.invoke_props_dialog(self, **dialog_options)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False

        if not context.window_manager.gabd_attributes_fetched:
            layout.prop(
                self,
                "fetch_requested",
                text="Scan",
                icon="FILE_REFRESH",
                toggle=True,
            )

        if context.window_manager.gabd_attribute_items:
            tools = layout.row(align=True)
            split = tools.split(factor=0.5, align=True)
            split.prop(
                context.window_manager,
                "gabd_attribute_filter",
                text="",
                icon="VIEWZOOM",
            )
            selection_tools = split.row(align=True)
            for action, label in (
                ("ALL", "All"),
                ("CLEAR", "Clear"),
                ("INVERT", "Invert"),
            ):
                operator = selection_tools.operator(
                    GABD_OT_BulkSelect.bl_idname,
                    text=label,
                )
                operator.action = action

            layout.template_list(
                GABD_UL_AttributeNames.bl_idname,
                "",
                context.window_manager,
                "gabd_attribute_items",
                context.window_manager,
                "gabd_attribute_index",
                rows=LIST_ROWS,
                maxrows=LIST_ROWS,
            )

            removals, affected_count, has_shared_mesh = checked_deletion_impact(
                context.window_manager.gabd_attribute_items
            )
            if removals:
                impact = layout.row()
                impact.alert = has_shared_mesh
                impact.label(
                    text=iface_("Delete {attributes} attributes · Affect {objects} objects").format(
                        attributes=removals,
                        objects=affected_count,
                    ),
                    icon="ERROR" if has_shared_mesh else "INFO",
                )
        elif context.window_manager.gabd_attributes_fetched:
            layout.label(text="No Attributes Found")
        else:
            layout.label(text="Scan Selected Mesh Attributes")

    def execute(self, context):
        names = {
            item.name
            for item in context.window_manager.gabd_attribute_items
            if item.selected
        }
        if not names:
            self.report({"WARNING"}, iface_("Select at least one attribute"))
            clear_attribute_state(context.window_manager)
            return {"CANCELLED"}

        removed = 0
        skipped = []
        for item in context.window_manager.gabd_attribute_items:
            if item.name not in names:
                continue
            for mesh_ref in item.meshes:
                data = mesh_ref.mesh
                if data is None:
                    continue
                attribute = data.attributes.get(item.name)
                if attribute is None:
                    skipped.append(
                        iface_("{mesh}: {attribute} (no longer exists)").format(
                            mesh=data.name,
                            attribute=item.name,
                        )
                    )
                    continue
                try:
                    data.attributes.remove(attribute)
                    removed += 1
                except RuntimeError:
                    # Built-in or otherwise protected attributes cannot be removed.
                    skipped.append(f"{data.name}: {attribute.name}")
                data.update()

        message = iface_("Removed {count} attributes").format(count=removed)
        if skipped:
            message += iface_("; skipped {count} protected attributes").format(
                count=len(skipped)
            )
        self.report({"INFO"}, message)
        clear_attribute_state(context.window_manager)
        return {"FINISHED"}

    def cancel(self, context):
        clear_attribute_state(context.window_manager)


def draw_attribute_manager_button(self, context):
    """The chosen compact placement directly below the native panel title."""
    layout = self.layout
    row = layout.row(align=True)
    row.alignment = "RIGHT"
    row.operator(
        GABD_OT_OpenManager.bl_idname,
        text="",
        icon="TRASH",
        emboss=True,
    )


CLASSES = (
    GABD_PG_ObjectRef,
    GABD_PG_MeshRef,
    GABD_PG_AttributeItem,
    GABD_OT_BulkSelect,
    GABD_OT_AttributeMetaInfo,
    GABD_OT_SelectAttributeObjects,
    GABD_UL_AttributeNames,
    GABD_OT_OpenManager,
)


def register_panel_button(panel_name):
    panel = getattr(bpy.types, panel_name, None)
    if panel is not None:
        panel.prepend(draw_attribute_manager_button)
        REGISTERED_PANEL_CALLBACKS.append((panel, draw_attribute_manager_button))


def register():
    try:
        bpy.app.translations.unregister(__name__)
    except Exception:
        pass
    bpy.app.translations.register(__name__, TRANSLATIONS)

    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.gabd_attribute_items = CollectionProperty(
        type=GABD_PG_AttributeItem,
        options={"SKIP_SAVE"},
    )
    bpy.types.WindowManager.gabd_attribute_index = IntProperty(
        get=get_inactive_attribute_index,
        set=ignore_attribute_index_change,
        options={"SKIP_SAVE"},
    )
    bpy.types.WindowManager.gabd_attributes_fetched = BoolProperty(
        default=False,
        options={"SKIP_SAVE"},
    )
    bpy.types.WindowManager.gabd_attribute_filter = StringProperty(
        name="Search Attributes",
        description="Filter scanned attributes by name",
        options={"SKIP_SAVE", "TEXTEDIT_UPDATE"},
    )

    # Mesh is the panel shown in the request.
    for panel_name in ("DATA_PT_mesh_attributes",):
        register_panel_button(panel_name)

def unregister():
    for panel, callback in REGISTERED_PANEL_CALLBACKS:
        try:
            panel.remove(callback)
        except (RuntimeError, ValueError):
            pass
    REGISTERED_PANEL_CALLBACKS.clear()

    for property_name in (
        "gabd_attribute_items",
        "gabd_attribute_index",
        "gabd_attributes_fetched",
        "gabd_attribute_filter",
    ):
        try:
            delattr(bpy.types.WindowManager, property_name)
        except AttributeError:
            pass
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    try:
        bpy.app.translations.unregister(__name__)
    except Exception:
        pass
