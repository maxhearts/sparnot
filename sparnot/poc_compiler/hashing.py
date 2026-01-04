"""Hashing utilities for IR change detection."""

import hashlib
import json
from typing import Dict, Any

from .models import NarrativeIR, CharacterIR, ArcIR, CompiledBundle


def hash_ir(ir: NarrativeIR) -> str:
    """Hash narrative IR deterministically."""
    # Use model_dump with sorted keys for deterministic JSON
    data = ir.model_dump(mode="json", exclude_none=False)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def hash_character_ir(char_ir: CharacterIR) -> str:
    """Hash character IR deterministically."""
    data = char_ir.model_dump(mode="json", exclude_none=False)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def hash_arc_ir(arc_ir: ArcIR) -> str:
    """Hash arc IR deterministically."""
    data = arc_ir.model_dump(mode="json", exclude_none=False)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def compute_bundle_hash(bundle: CompiledBundle) -> str:
    """Compute hash of entire bundle (excluding hashes field)."""
    # Create a copy without the hashes field
    data = bundle.model_dump(mode="json", exclude_none=False)
    data.pop("hashes", None)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def compute_all_hashes(bundle: CompiledBundle) -> Dict[str, Any]:
    """Compute all hashes for a bundle."""
    hashes = {
        "bundle": compute_bundle_hash(bundle),
    }
    
    # Hash narrative IR
    narrative_ir = NarrativeIR(**bundle.ir["narrative_ir"])
    hashes["narrative_ir"] = hash_ir(narrative_ir)
    
    # Hash character IRs
    hashes["character_irs"] = {}
    for char_ir_data in bundle.ir["character_irs"]:
        char_ir = CharacterIR(**char_ir_data)
        hashes["character_irs"][char_ir.character_id] = hash_character_ir(char_ir)
    
    # Hash arc IR if present
    if bundle.ir.get("arc_ir"):
        arc_ir = ArcIR(**bundle.ir["arc_ir"])
        hashes["arc_ir"] = hash_arc_ir(arc_ir)
    else:
        hashes["arc_ir"] = None
    
    return hashes

