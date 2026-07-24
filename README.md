# Attribute Sweep

Attribute Sweep is a small cleanup tool for mesh attributes you do not need
anymore. Pick a group of mesh objects, scan them, and clean up the attributes
you choose.

It is handy after importing assets, testing Geometry Nodes, or any time a bunch
of objects have picked up leftover attributes. You can see what will change
before deleting anything.

## What It Helps With

- Gives you one list of the attributes found on the selected mesh objects.
- Shows the attribute type and where it lives, and points out when the same
  name means different things on different meshes.
- Lets you select the objects that use an attribute, so you can check them
  before removing it.
- Lets you search the list and select, clear, or invert several entries at once.
- Tells you how many attributes and objects will change. It also warns you when
  the mesh data is shared by other objects.
- Leaves Blender's internal and required attributes alone.

## What It Does Not Try To Do

Attribute Sweep does not create attributes, change their values, or rename
them. It is just for finding and clearing unwanted attributes from a group of
objects.

## Installation

In Blender 4.2 or newer, install the packaged extension from Preferences > Get
Extensions > Install from Disk, then enable Attribute Sweep.

## Usage

1. Select the mesh objects you want to clean up.
2. Open **Object Data Properties > Attributes**.
3. Click the trash-can button next to the Attributes panel title.
4. Click **Scan** to see what attributes they have.
5. Check or filter the list. You can also use the button on a row to select the
   objects that use that attribute.
6. Select the unwanted attributes and click **Delete**.

## License

GPL-3.0-or-later. See `blender_manifest.toml` for extension metadata.
