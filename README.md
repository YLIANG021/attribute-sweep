# Attribute Sweep

Attribute Sweep is a focused cleanup tool for mesh attributes. It inventories
the attributes used by a selection of mesh objects, helps trace where each one
is stored, then removes only the attributes you explicitly approve.

It is built for the awkward cleanup pass: imported assets, experiments, or
Geometry Nodes workflows can leave a selection with attributes that are no
longer needed. Attribute Sweep makes the destructive step inspectable first.

## Audit Before Cleanup

- Builds one inventory row per attribute name across the selected mesh objects.
- Shows each attribute's domain and data type, and flags the names whose
  definition differs between meshes.
- Lets you select the objects that contain a scanned attribute, so a result can
  be inspected in context before it is removed.
- Searches, selects, clears, or inverts the current cleanup list in batches.
- Calculates how many attributes and object users will be affected. A warning
  appears when deletion changes shared mesh data.
- Skips Blender internal and required attributes during the scan.

## Purposeful Scope

Attribute Sweep does not create attributes, edit their values, or rename them.
It stays narrowly focused on reviewing and removing unwanted attributes across
a multi-object selection.

## Installation

In Blender 4.2 or newer, install the packaged extension from Preferences > Get
Extensions > Install from Disk, then enable Attribute Sweep.

## Usage

1. Select the mesh objects to audit.
2. Open **Object Data Properties > Attributes**.
3. Click the trash-can button next to the Attributes panel title.
4. Click **Scan** to build the attribute inventory.
5. Inspect or filter the results, and optionally use the object-selection
   button on a row to locate its users.
6. Select the unwanted attributes and click **Delete**.

## License

GPL-3.0-or-later. See `blender_manifest.toml` for extension metadata.
