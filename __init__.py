import unrealsdk

from mods_base import SliderOption, hook, build_mod
from unrealsdk.hooks import Type

weapon_bone_scale = SliderOption(
    identifier="Weapon Bone Scale",
    value=200,
    min_value=50,
    max_value=300,
    step=5,
    is_integer=True,
    description="Scale of weapon-related bones. 100% = normal."
)

CONTROL_PREFIX = "WeaponBoneScale"

def find_anim_tree(mesh):
    try:
        for control in mesh.SkelControlTickArray:
            if control is None:
                continue

            try:
                outer = control.Outer

                if (outer is not None and outer.Class.Name == "WillowAnimTree"):
                    return outer

            except Exception:
                pass

    except Exception as e:
        print(f"AnimTree search failed: {e}")

    return None


def find_existing_control(anim_tree, control_name):
    try:
        for control_list in anim_tree.SkelControlLists:
            try:
                control = control_list.ControlHead

                while control is not None:
                    if getattr(control, "ControlName", None) == control_name:
                        return control

                    control = getattr(control, "NextControl", None)

            except Exception:
                pass

    except Exception as e:
        print(f"Existing control search failed for {control_name}: {e}")

    return None


def get_skel_control_list_struct(anim_tree):
    try:
        array_prop = anim_tree.Class._find_prop("SkelControlLists")

        if array_prop is None:
            return None

        inner = getattr(array_prop, "Inner", None)

        if inner is None:
            return None

        return getattr(inner, "Struct", None)

    except Exception as e:
        print(f"Struct discovery failed: {e}")
        return None


def register_control(anim_tree, bone_name, control):
    try:
        lists = anim_tree.SkelControlLists

        for control_list in lists:
            try:
                if control_list.BoneName != bone_name:
                    continue

                old_head = control_list.ControlHead

                if old_head is not None:
                    control.NextControl = old_head

                control_list.ControlHead = control
                return True

            except Exception:
                pass

        struct_type = get_skel_control_list_struct(anim_tree)

        if struct_type is None:
            return False

        entry = unrealsdk.unreal.WrappedStruct(struct_type)
        entry.BoneName = bone_name
        entry.ControlHead = control

        lists.append(entry)

        return True

    except Exception as e:
        print(f"[{bone_name}] Register failed: {e}")
        return False


def configure_weapon_bone(control):
    scale = int(weapon_bone_scale.value) / 100.0

    control.BoneScale = scale
    control.ControlStrength = 1.0
    control.StrengthTarget = 1.0
    control.IgnoreAtOrAboveLOD = 1000
    control.bIgnoreWhenNotRendered = False

    try:
        control.SetSkelControlActive(True)
    except Exception:
        pass

    try:
        control.SetSkelControlStrength(1.0, 0.0)
    except Exception:
        pass

    for property_name in (
        "bAddTranslation",
        "bApplyTranslation",
        "bAddRotation",
        "bApplyRotation",
    ):
        try:
            setattr(control, property_name, False)
        except Exception:
            pass

    return control


def create_weapon_bone_control(anim_tree, bone_index, bone_name):
    control_name = f"{CONTROL_PREFIX}_{bone_index}_{bone_name}"

    try:
        control = find_existing_control(
            anim_tree,
            control_name,
        )

        if control is None:
            control_class = unrealsdk.find_class("SkelControlSingleBone")

            control = unrealsdk.construct_object(control_class, outer=anim_tree)

            if control is None:
                return None

            control.ControlName = control_name

            if not register_control(anim_tree, bone_name, control):
                return None

        return configure_weapon_bone(control)

    except Exception as e:
        print(
            f"[{bone_index:03d}] "
            f"{bone_name}: failed: {e}"
        )
        return None


def scale_weapon_bones(pawn):
    try:
        mesh = pawn.Mesh

        if mesh is None:
            return

        anim_tree = find_anim_tree(mesh)

        if anim_tree is None:
            return

        found = False

        for bone_index in range(50):
            try:
                bone_name = mesh.GetBoneName(bone_index)
            except Exception:
                break

            if bone_name is None:
                continue

            if "Weapon" not in bone_name:
                continue

            found = True

            create_weapon_bone_control(anim_tree, bone_index, bone_name)

        if not found:
            return

        mesh.InitSkelControls()

    except Exception as e:
        print(f"Weapon bone scaling failed: {e}")


@hook("WillowGame.WillowAIPawn:PostSpawn", Type.POST)
def pawn_spawned(obj, args, ret, func):
    scale_weapon_bones(obj)


mod = build_mod(
    options=[
        weapon_bone_scale
    ]
)