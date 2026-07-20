"""
Semantic map viewer - visualize concept graph.
"""

import logging
from typing import Optional, List, Dict

from ..database import ConceptNode, ConceptEdge, get_session

logger = logging.getLogger(__name__)


class SemanticViewer:
    """View and explore concept graph."""

    def __init__(self):
        pass

    def get_node(self, node_id: int) -> Optional[ConceptNode]:
        """Get concept node by ID."""
        with get_session() as session:
            return session.query(ConceptNode).filter_by(id=node_id).first()

    def get_neighbors(self, node_id: int, edge_type: str = None) -> List[tuple]:
        """
        Get neighboring nodes.

        Args:
            node_id: Source node ID
            edge_type: Filter by edge type (optional)

        Returns:
            List of (node, edge) tuples
        """
        with get_session() as session:
            query = session.query(ConceptEdge).filter_by(source_id=node_id)

            if edge_type:
                query = query.filter_by(edge_type=edge_type)

            edges = query.all()

            neighbors = []
            for edge in edges:
                target_node = session.query(ConceptNode).filter_by(
                    id=edge.target_id
                ).first()

                if target_node:
                    neighbors.append((target_node, edge))

            return neighbors

    def display_node(self, node: ConceptNode):
        """Display node information."""
        print(f"\n{'=' * 70}")
        print(f"CONCEPT NODE #{node.id}: {node.label.upper()}")
        print(f"{'=' * 70}")

        print(f"\nType: {node.node_type}")

        if node.ontology_refs:
            print(f"\nOntology References:")
            for key, value in node.ontology_refs.items():
                print(f"  {key}: {value}")

        # Get neighbors
        neighbors = self.get_neighbors(node.id)

        if neighbors:
            print(f"\nConnections ({len(neighbors)} total):")

            # Group by edge type
            by_type = {}
            for target, edge in neighbors:
                if edge.edge_type not in by_type:
                    by_type[edge.edge_type] = []
                by_type[edge.edge_type].append((target, edge.weight))

            for edge_type, connections in by_type.items():
                print(f"\n  {edge_type}:")
                # Sort by weight
                connections.sort(key=lambda x: x[1], reverse=True)

                for target, weight in connections[:5]:
                    print(f"    → {target.label} (weight={weight:.2f})")

                if len(connections) > 5:
                    print(f"    ... and {len(connections) - 5} more")

        print(f"\n{'=' * 70}\n")

    def find_path(self, source_id: int, target_id: int, max_depth: int = 3) -> Optional[List]:
        """
        Find path between two nodes (BFS).

        Args:
            source_id: Source node ID
            target_id: Target node ID
            max_depth: Maximum path length

        Returns:
            List of node IDs forming path, or None
        """
        if source_id == target_id:
            return [source_id]

        visited = set()
        queue = [(source_id, [source_id])]

        with get_session() as session:
            while queue:
                current_id, path = queue.pop(0)

                if len(path) > max_depth:
                    continue

                if current_id in visited:
                    continue

                visited.add(current_id)

                # Get neighbors
                edges = session.query(ConceptEdge).filter_by(
                    source_id=current_id
                ).all()

                for edge in edges:
                    next_id = edge.target_id

                    if next_id == target_id:
                        return path + [next_id]

                    if next_id not in visited:
                        queue.append((next_id, path + [next_id]))

        return None

    def display_path(self, path: List[int]):
        """Display path between nodes."""
        if not path:
            print("\nNo path found.")
            return

        print(f"\nPath (length {len(path) - 1}):")

        with get_session() as session:
            for i, node_id in enumerate(path):
                node = session.query(ConceptNode).filter_by(id=node_id).first()

                if i > 0:
                    # Get edge
                    edge = session.query(ConceptEdge).filter_by(
                        source_id=path[i-1],
                        target_id=node_id
                    ).first()

                    edge_label = f"--[{edge.edge_type}]-->" if edge else "-->"
                    print(f"  {edge_label}")

                print(f"  {node.label} (#{node.id})")

        print()

    def list_nodes(self, node_type: str = None, limit: int = 20):
        """List concept nodes."""
        with get_session() as session:
            query = session.query(ConceptNode)

            if node_type:
                query = query.filter_by(node_type=node_type)

            nodes = query.limit(limit).all()

        print(f"\nConcept Nodes ({len(nodes)} shown):")
        print(f"\n{'ID':<6} {'Type':<10} {'Label':<30} {'Connections'}")
        print("-" * 70)

        with get_session() as session:
            for node in nodes:
                # Count connections
                conn_count = session.query(ConceptEdge).filter_by(
                    source_id=node.id
                ).count()

                print(f"{node.id:<6} "
                      f"{node.node_type:<10} "
                      f"{node.label:<30} "
                      f"{conn_count}")

        print()

    def get_graph_stats(self) -> Dict:
        """Get graph statistics."""
        with get_session() as session:
            node_count = session.query(ConceptNode).count()

            edge_types = {}
            edges = session.query(ConceptEdge).all()

            for edge in edges:
                edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1

        return {
            'nodes': node_count,
            'total_edges': len(edges),
            'edge_types': edge_types
        }


def main():
    """CLI for semantic viewer."""
    import argparse

    parser = argparse.ArgumentParser(description="Semantic Map Viewer")
    parser.add_argument(
        '--node',
        type=int,
        help='View specific node'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all nodes'
    )
    parser.add_argument(
        '--path',
        nargs=2,
        type=int,
        metavar=('SOURCE', 'TARGET'),
        help='Find path between nodes'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show graph statistics'
    )
    parser.add_argument(
        '--type',
        type=str,
        choices=['concept', 'motif'],
        help='Filter by node type'
    )

    args = parser.parse_args()

    viewer = SemanticViewer()

    if args.node:
        node = viewer.get_node(args.node)
        if node:
            viewer.display_node(node)
        else:
            print(f"\nNode #{args.node} not found.")

    elif args.path:
        source_id, target_id = args.path
        path = viewer.find_path(source_id, target_id)
        viewer.display_path(path)

    elif args.list:
        viewer.list_nodes(node_type=args.type)

    elif args.stats:
        stats = viewer.get_graph_stats()
        print("\nConcept Graph Statistics:")
        print(f"  Nodes: {stats['nodes']}")
        print(f"  Total Edges: {stats['total_edges']}")
        print(f"\n  Edge Types:")
        for edge_type, count in stats['edge_types'].items():
            print(f"    {edge_type}: {count}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
