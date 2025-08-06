# routes/export_import.py
import logging
from typing import Dict, Any
from flask import Blueprint, request, jsonify, make_response, g
from services.flow_serializer import FlowSerializer
from database import get_flow, list_flows
from component_manager import discover_tframex_components
from middleware.auth import require_auth, get_current_user_id
from auth.rbac import require_permission

logger = logging.getLogger("ExportImportAPI")

export_import_bp = Blueprint('export_import', __name__, url_prefix='/api/tframex')

def get_global_tframex_app():
    """Get the global TFrameX app instance"""
    from tframex_config import get_tframex_app_instance
    return get_tframex_app_instance()

@export_import_bp.route('/flows/<flow_id>/export', methods=['GET'])
@require_auth
@require_permission('flows.read')
def export_flow(flow_id):
    """Export a flow to specified format"""
    logger.info(f"Export request for flow {flow_id}")
    
    try:
        # Get format from query params
        format_type = request.args.get('format', 'json').lower()
        
        if format_type not in FlowSerializer.SUPPORTED_FORMATS:
            return jsonify({
                "error": f"Unsupported format: {format_type}. Supported: {FlowSerializer.SUPPORTED_FORMATS}"
            }), 400
        
        # Get flow from database or use current flow from request body
        if flow_id == 'current':
            # Export current flow from request body
            flow_data = request.get_json() if request.is_json else {}
            if not flow_data.get('nodes'):
                return jsonify({"error": "No flow data provided"}), 400
        else:
            # Get saved flow from database
            flow_data = get_flow(flow_id)
            if not flow_data:
                return jsonify({"error": "Flow not found"}), 404
        
        # Export flow
        exported_content = FlowSerializer.export_flow(flow_data, format_type)
        
        # Set appropriate content type and filename
        content_type_map = {
            'json': 'application/json',
            'yaml': 'application/x-yaml',
            'mermaid': 'text/plain'
        }
        
        file_extension_map = {
            'json': 'json',
            'yaml': 'yaml',
            'mermaid': 'mmd'
        }
        
        flow_name = flow_data.get('name', 'flow').replace(' ', '_').lower()
        filename = f"{flow_name}.{file_extension_map[format_type]}"
        
        response = make_response(exported_content)
        response.headers['Content-Type'] = content_type_map[format_type]
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Successfully exported flow {flow_id} as {format_type}")
        return response
        
    except Exception as e:
        logger.error(f"Error exporting flow {flow_id}: {e}", exc_info=True)
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@export_import_bp.route('/flows/export-current', methods=['POST'])
@require_auth
@require_permission('flows.read')
def export_current_flow():
    """Export the current flow being edited (not saved to database)"""
    logger.info("Export request for current flow")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No flow data provided"}), 400
        
        format_type = data.get('format', 'json').lower()
        
        if format_type not in FlowSerializer.SUPPORTED_FORMATS:
            return jsonify({
                "error": f"Unsupported format: {format_type}. Supported: {FlowSerializer.SUPPORTED_FORMATS}"
            }), 400
        
        # Extract flow data
        flow_data = {
            "name": data.get('name', 'Current Flow'),
            "description": data.get('description', ''),
            "nodes": data.get('nodes', []),
            "edges": data.get('edges', [])
        }
        
        if not flow_data['nodes']:
            return jsonify({"error": "No nodes in flow"}), 400
        
        # Export flow
        exported_content = FlowSerializer.export_flow(flow_data, format_type)
        
        # Return as JSON response with content
        return jsonify({
            "content": exported_content,
            "format": format_type,
            "filename": f"{flow_data['name'].replace(' ', '_').lower()}.{format_type}"
        })
        
    except Exception as e:
        logger.error(f"Error exporting current flow: {e}", exc_info=True)
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@export_import_bp.route('/flows/import', methods=['POST'])
@require_auth  
@require_permission('flows.read')  # Changed from flows.create for development - users with read access can import
def import_flow():
    """Import a flow from file content"""
    logger.info("Import request received")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        content = data.get('content')
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        format_type = data.get('format')  # Optional, will auto-detect if not provided
        
        # Import and normalize flow
        imported_flow = FlowSerializer.import_flow(content, format_type)
        
        # Get available components for validation
        global_tframex_app = get_global_tframex_app()
        available_components = discover_tframex_components(app_instance=global_tframex_app)
        
        # Validate dependencies
        missing_deps = FlowSerializer.validate_dependencies(imported_flow, available_components)
        
        # Apply auto-layout to imported nodes to avoid overlaps
        positioned_flow = _apply_import_layout(imported_flow)
        
        response_data = {
            "success": True,
            "flow": positioned_flow,
            "missing_dependencies": missing_deps,
            "warnings": []
        }
        
        # Add warnings for missing dependencies
        if any(missing_deps.values()):
            response_data["warnings"].append("Some components or models may not be available")
        
        logger.info("Successfully imported flow")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error importing flow: {e}", exc_info=True)
        return jsonify({"error": f"Import failed: {str(e)}"}), 500

@export_import_bp.route('/flows/import/validate', methods=['POST'])
@require_auth
def validate_import():
    """Validate import content without actually importing"""
    logger.info("Import validation request received")
    
    try:
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "No content provided"}), 400
        
        # Try to detect format
        try:
            format_type = FlowSerializer._detect_format(content)
        except ValueError as e:
            return jsonify({
                "valid": False,
                "error": str(e),
                "detected_format": None
            })
        
        # Try to parse content
        try:
            imported_flow = FlowSerializer.import_flow(content, format_type)
            
            # Basic validation
            nodes_count = len(imported_flow.get("nodes", []))
            edges_count = len(imported_flow.get("edges", []))
            
            return jsonify({
                "valid": True,
                "detected_format": format_type,
                "preview": {
                    "name": imported_flow.get("metadata", {}).get("name", "Imported Flow"),
                    "nodes_count": nodes_count,
                    "edges_count": edges_count,
                    "dependencies": imported_flow.get("dependencies", {})
                }
            })
            
        except Exception as parse_error:
            return jsonify({
                "valid": False,
                "error": f"Parse error: {str(parse_error)}",
                "detected_format": format_type
            })
            
    except Exception as e:
        logger.error(f"Error validating import: {e}", exc_info=True)
        return jsonify({"error": f"Validation failed: {str(e)}"}), 500

def _apply_import_layout(flow_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply auto-layout to imported flow to avoid overlapping with existing nodes"""
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])
    
    if not nodes:
        return flow_data
    
    # Simple grid layout for imported nodes
    cols = 3
    spacing_x = 250
    spacing_y = 200
    start_x = 100
    start_y = 100
    
    for i, node in enumerate(nodes):
        row = i // cols
        col = i % cols
        
        node["position"] = {
            "x": start_x + (col * spacing_x),
            "y": start_y + (row * spacing_y)
        }
    
    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": flow_data.get("metadata", {}),
        "dependencies": flow_data.get("dependencies", {})
    }