# services/flow_serializer.py
import json
import yaml
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
import logging
import nanoid

logger = logging.getLogger("FlowSerializer")

class FlowSerializer:
    """Handles serialization and deserialization of flows to/from various formats"""
    
    SUPPORTED_FORMATS = ["json", "yaml", "mermaid"]
    CURRENT_VERSION = "1.0.0"
    
    @classmethod
    def export_flow(cls, flow_data: Dict[str, Any], format_type: str) -> str:
        """Export flow to specified format"""
        if format_type not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format_type}. Supported: {cls.SUPPORTED_FORMATS}")
        
        # Normalize flow data for export
        normalized_flow = cls._normalize_for_export(flow_data)
        
        if format_type == "json":
            return cls._export_json(normalized_flow)
        elif format_type == "yaml":
            return cls._export_yaml(normalized_flow)
        elif format_type == "mermaid":
            return cls._export_mermaid(normalized_flow)
    
    @classmethod
    def import_flow(cls, content: str, format_type: Optional[str] = None) -> Dict[str, Any]:
        """Import flow from content, auto-detecting format if not specified"""
        if format_type is None:
            format_type = cls._detect_format(content)
        
        if format_type == "json":
            return cls._import_json(content)
        elif format_type == "yaml":
            return cls._import_yaml(content)
        else:
            raise ValueError(f"Unsupported import format: {format_type}")
    
    @classmethod
    def _normalize_for_export(cls, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize flow data for export - remove UI-only data, add metadata"""
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])
        
        # Clean nodes - remove position and other UI-only data for portable export
        clean_nodes = []
        for node in nodes:
            clean_node = {
                "id": node.get("id"),
                "type": node.get("type"),
                "data": node.get("data", {}),
                "position": node.get("position", {"x": 0, "y": 0})  # Keep position for layout
            }
            clean_nodes.append(clean_node)
        
        # Clean edges - keep essential connection data
        clean_edges = []
        for edge in edges:
            clean_edge = {
                "id": edge.get("id"),
                "source": edge.get("source"),
                "target": edge.get("target"),
                "sourceHandle": edge.get("sourceHandle"),
                "targetHandle": edge.get("targetHandle"),
                "type": edge.get("type", "smoothstep")
            }
            clean_edges.append(clean_edge)
        
        # Detect dependencies
        dependencies = cls._detect_dependencies(clean_nodes)
        
        return {
            "version": cls.CURRENT_VERSION,
            "metadata": {
                "name": flow_data.get("name", "Exported Flow"),
                "description": flow_data.get("description", ""),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "tframex_version": "1.1.0"
            },
            "nodes": clean_nodes,
            "edges": clean_edges,
            "dependencies": dependencies
        }
    
    @classmethod
    def _detect_dependencies(cls, nodes: List[Dict]) -> Dict[str, List[str]]:
        """Detect required dependencies from nodes"""
        custom_components = set()
        required_models = set()
        mcp_servers = set()
        
        for node in nodes:
            node_type = node.get("type", "")
            node_data = node.get("data", {})
            
            # Detect custom components (non-standard node types)
            if node_type not in ["ConversationalAssistant", "FlowBuilderAgent", "Sequential", "Parallel", "Router", "Discussion", "textInput"]:
                custom_components.add(node_type)
            
            # Detect model requirements
            if "model" in node_data and node_data["model"]:
                required_models.add(node_data["model"])
            
            # Detect MCP servers
            if "connected_mcp_servers" in node_data:
                for server in node_data["connected_mcp_servers"]:
                    if server:
                        mcp_servers.add(server)
        
        return {
            "custom_components": list(custom_components),
            "required_models": list(required_models),
            "mcp_servers": list(mcp_servers)
        }
    
    @classmethod
    def _export_json(cls, flow_data: Dict[str, Any]) -> str:
        """Export to JSON format"""
        return json.dumps(flow_data, indent=2, ensure_ascii=False)
    
    @classmethod
    def _export_yaml(cls, flow_data: Dict[str, Any]) -> str:
        """Export to YAML format with simplified structure"""
        # Create simplified YAML structure
        yaml_data = {
            "version": flow_data["version"],
            "metadata": flow_data["metadata"],
            "flow": {
                "agents": [],
                "patterns": [],
                "tools": [],
                "connections": []
            },
            "dependencies": flow_data["dependencies"]
        }
        
        # Categorize nodes
        for node in flow_data["nodes"]:
            node_data = node.get("data", {})
            component_category = node_data.get("component_category", "unknown")
            
            simplified_node = {
                "id": node["id"],
                "type": node["type"],
                "label": node_data.get("label", node["type"])
            }
            
            # Add relevant config based on type
            if component_category == "agent":
                config = {}
                if node_data.get("system_prompt_override"):
                    config["system_prompt"] = node_data["system_prompt_override"]
                if node_data.get("model"):
                    config["model"] = node_data["model"]
                if node_data.get("selected_tools"):
                    config["tools"] = node_data["selected_tools"]
                if config:
                    simplified_node["config"] = config
                yaml_data["flow"]["agents"].append(simplified_node)
            
            elif component_category == "pattern":
                # Add pattern-specific config
                config = {}
                for key, value in node_data.items():
                    if key not in ["label", "component_category", "tframex_component_id"] and value is not None:
                        config[key] = value
                if config:
                    simplified_node["config"] = config
                yaml_data["flow"]["patterns"].append(simplified_node)
            
            elif component_category == "tool":
                yaml_data["flow"]["tools"].append(simplified_node)
        
        # Add connections
        for edge in flow_data["edges"]:
            connection = {
                "from": edge["source"],
                "to": edge["target"],
                "type": "data_flow"
            }
            if edge.get("sourceHandle"):
                connection["source_handle"] = edge["sourceHandle"]
            if edge.get("targetHandle"):
                connection["target_handle"] = edge["targetHandle"]
            yaml_data["flow"]["connections"].append(connection)
        
        return yaml.dump(yaml_data, default_flow_style=False, indent=2, allow_unicode=True)
    
    @classmethod
    def _export_mermaid(cls, flow_data: Dict[str, Any]) -> str:
        """Export to Mermaid diagram format"""
        nodes = flow_data["nodes"]
        edges = flow_data["edges"]
        
        mermaid_lines = [
            "graph TD",
            f"    %% {flow_data['metadata']['name']}",
            f"    %% Generated on {flow_data['metadata']['exported_at']}"
        ]
        
        # Create node definitions
        node_definitions = {}
        for node in nodes:
            node_id = node["id"].replace("-", "_")  # Mermaid doesn't like hyphens
            node_data = node.get("data", {})
            label = node_data.get("label", node["type"])
            component_category = node_data.get("component_category", "")
            
            # Choose shape based on component type
            if component_category == "agent":
                shape_start, shape_end = "[", "]"
                css_class = "agent"
            elif component_category == "pattern":
                shape_start, shape_end = "{", "}"
                css_class = "pattern"
            elif component_category == "tool":
                shape_start, shape_end = "((", "))"
                css_class = "tool"
            else:
                shape_start, shape_end = "(", ")"
                css_class = "utility"
            
            node_def = f"    {node_id}{shape_start}{label}<br/>{node['type']}{shape_end}"
            mermaid_lines.append(node_def)
            node_definitions[node["id"]] = {"mermaid_id": node_id, "class": css_class}
        
        mermaid_lines.append("")
        
        # Add connections
        for edge in edges:
            source_id = node_definitions.get(edge["source"], {}).get("mermaid_id", edge["source"])
            target_id = node_definitions.get(edge["target"], {}).get("mermaid_id", edge["target"])
            
            # Choose arrow style based on connection type
            arrow_style = "-->"
            if edge.get("data", {}).get("connectionType") == "toolAttachment":
                arrow_style = "-.->|tool|"
            elif edge.get("data", {}).get("connectionType") == "agentInstanceToPatternParam":
                arrow_style = "-->|config|"
            
            mermaid_lines.append(f"    {source_id} {arrow_style} {target_id}")
        
        # Add CSS classes
        mermaid_lines.extend([
            "",
            "    classDef agent fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
            "    classDef pattern fill:#f3e5f5,stroke:#4a148c,stroke-width:2px", 
            "    classDef tool fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px",
            "    classDef utility fill:#fff3e0,stroke:#ef6c00,stroke-width:2px"
        ])
        
        # Apply classes
        for node_id, node_info in node_definitions.items():
            mermaid_lines.append(f"    class {node_info['mermaid_id']} {node_info['class']}")
        
        return "\n".join(mermaid_lines)
    
    @classmethod
    def _detect_format(cls, content: str) -> str:
        """Auto-detect format from content"""
        content_stripped = content.strip()
        
        if content_stripped.startswith("{") or content_stripped.startswith("["):
            return "json"
        elif content_stripped.startswith("graph ") or content_stripped.startswith("flowchart "):
            return "mermaid"
        elif "version:" in content_stripped or content_stripped.startswith("version:"):
            return "yaml"
        else:
            # Try to parse as JSON first
            try:
                json.loads(content)
                return "json"
            except json.JSONDecodeError:
                pass
            
            # Try YAML
            try:
                yaml.safe_load(content)
                return "yaml"
            except yaml.YAMLError:
                pass
        
        raise ValueError("Could not detect format from content")
    
    @classmethod
    def _import_json(cls, content: str) -> Dict[str, Any]:
        """Import from JSON format"""
        try:
            data = json.loads(content)
            return cls._normalize_for_import(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    @classmethod
    def _import_yaml(cls, content: str) -> Dict[str, Any]:
        """Import from YAML format"""
        try:
            data = yaml.safe_load(content)
            return cls._normalize_for_import(data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
    
    @classmethod
    def _normalize_for_import(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize imported data to ReactFlow format"""
        # If it's already in ReactFlow format (JSON export), return as-is with new IDs
        if "nodes" in data and "edges" in data:
            return cls._regenerate_ids(data)
        
        # If it's simplified YAML format, convert to ReactFlow format
        if "flow" in data:
            return cls._convert_yaml_to_reactflow(data)
        
        raise ValueError("Unrecognized flow format")
    
    @classmethod
    def _regenerate_ids(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate IDs to avoid conflicts with existing flows"""
        import nanoid
        
        # Create ID mapping
        id_mapping = {}
        
        # Regenerate node IDs
        nodes = []
        for node in data.get("nodes", []):
            old_id = node["id"]
            new_id = f"{node['type']}-{nanoid.generate(size=6)}"
            id_mapping[old_id] = new_id
            
            new_node = {**node, "id": new_id}
            nodes.append(new_node)
        
        # Update edge IDs and references
        edges = []
        for edge in data.get("edges", []):
            new_edge = {
                **edge,
                "id": f"edge-{nanoid.generate(size=8)}",
                "source": id_mapping.get(edge["source"], edge["source"]),
                "target": id_mapping.get(edge["target"], edge["target"])
            }
            edges.append(new_edge)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": data.get("metadata", {}),
            "dependencies": data.get("dependencies", {})
        }
    
    @classmethod
    def _convert_yaml_to_reactflow(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert simplified YAML format to ReactFlow format"""
        import nanoid
        
        flow_data = data.get("flow", {})
        nodes = []
        edges = []
        id_mapping = {}
        
        # Convert agents
        for agent in flow_data.get("agents", []):
            node_id = f"{agent['type']}-{nanoid.generate(size=6)}"
            id_mapping[agent["id"]] = node_id
            
            # Build node data
            node_data = {
                "label": agent.get("label", agent["type"]),
                "component_category": "agent",
                "tframex_component_id": agent["type"]
            }
            
            # Add config if present
            config = agent.get("config", {})
            if "system_prompt" in config:
                node_data["system_prompt_override"] = config["system_prompt"]
            if "model" in config:
                node_data["model"] = config["model"]
            if "tools" in config:
                node_data["selected_tools"] = config["tools"]
            
            node = {
                "id": node_id,
                "type": agent["type"],
                "position": {"x": 100, "y": 100},  # Will be auto-layouted
                "data": node_data
            }
            nodes.append(node)
        
        # Convert patterns
        for pattern in flow_data.get("patterns", []):
            node_id = f"{pattern['type']}-{nanoid.generate(size=6)}"
            id_mapping[pattern["id"]] = node_id
            
            node_data = {
                "label": pattern.get("label", pattern["type"]),
                "component_category": "pattern",
                "tframex_component_id": pattern["type"]
            }
            
            # Add pattern-specific config
            config = pattern.get("config", {})
            node_data.update(config)
            
            node = {
                "id": node_id,
                "type": pattern["type"],
                "position": {"x": 300, "y": 100},  # Will be auto-layouted
                "data": node_data
            }
            nodes.append(node)
        
        # Convert tools
        for tool in flow_data.get("tools", []):
            node_id = f"{tool['type']}-{nanoid.generate(size=6)}"
            id_mapping[tool["id"]] = node_id
            
            node_data = {
                "label": tool.get("label", tool["type"]),
                "component_category": "tool",
                "tframex_component_id": tool["type"]
            }
            
            node = {
                "id": node_id,
                "type": tool["type"],
                "position": {"x": 500, "y": 100},  # Will be auto-layouted
                "data": node_data
            }
            nodes.append(node)
        
        # Convert connections
        for connection in flow_data.get("connections", []):
            source_id = id_mapping.get(connection["from"])
            target_id = id_mapping.get(connection["to"])
            
            if source_id and target_id:
                edge = {
                    "id": f"edge-{nanoid.generate(size=8)}",
                    "source": source_id,
                    "target": target_id,
                    "type": "smoothstep"
                }
                
                if "source_handle" in connection:
                    edge["sourceHandle"] = connection["source_handle"]
                if "target_handle" in connection:
                    edge["targetHandle"] = connection["target_handle"]
                
                edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": data.get("metadata", {}),
            "dependencies": data.get("dependencies", {})
        }

    @classmethod
    def validate_dependencies(cls, flow_data: Dict[str, Any], available_components: Dict[str, List]) -> Dict[str, List[str]]:
        """Validate that all dependencies are available"""
        dependencies = flow_data.get("dependencies", {})
        missing = {
            "custom_components": [],
            "required_models": [],
            "mcp_servers": []
        }
        
        # Check custom components
        available_component_ids = set()
        for category in available_components.values():
            for comp in category:
                available_component_ids.add(comp.get("id", ""))
        
        for comp in dependencies.get("custom_components", []):
            if comp not in available_component_ids:
                missing["custom_components"].append(comp)
        
        # Note: Model and MCP server validation would need access to current configs
        # For now, just return the structure
        
        return missing