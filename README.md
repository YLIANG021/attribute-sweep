# Attribute Sweep

Attribute Sweep is a Blender extension for scanning and safely removing mesh
attributes across multiple selected objects.

## Features

- Scans manageable geometry attributes on selected mesh objects.
- Filters and batch-selects attributes by name.
- Shows attribute domain and data type, including mismatches across meshes.
- Selects the objects containing a scanned attribute.
- Shows the number of affected objects and warns when shared mesh data will be
  affected before deletion.

## Installation

In Blender 4.2 or newer, install the packaged extension from Preferences > Get
Extensions > Install from Disk, then enable Attribute Sweep.

## Usage

1. Select one or more mesh objects.
2. Open Object Data Properties > Attributes.
3. Click the trash-can button beside the Attributes panel title.
4. Click **Scan**, select the attributes to remove, then click **Delete**.

## License

GPL-3.0-or-later. See `blender_manifest.toml` for extension metadata.
