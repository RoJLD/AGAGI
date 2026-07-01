import { useEffect, useRef } from "react";
import { select } from "d3-selection";
import {
  forceSimulation,
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import { drag } from "d3-drag";
import type { ProvNode, ProvEdge, ProvNodeType } from "../lib/provenance";
import { vizColors } from "../theme";

type NodeDatum = ProvNode & SimulationNodeDatum & { fx?: number | null; fy?: number | null };
type LinkDatum = SimulationLinkDatum<NodeDatum>;

interface ProvenanceGraphProps {
  nodes: ProvNode[];
  edges: ProvEdge[];
  onSelect: (node: ProvNode) => void;
}

export function ProvenanceGraph({ nodes, edges, onSelect }: ProvenanceGraphProps) {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!ref.current || !nodes.length) return;
    const viz = vizColors();
    const colorOf = (t: ProvNodeType) => (t === "condition" ? viz[0] : t === "edr" ? viz[1] : viz[2]);

    const svg = select(ref.current);
    svg.selectAll("*").remove();
    const width = ref.current.clientWidth || 800;
    const height = ref.current.clientHeight || 500;

    // Copies locales : d3 mute les data (positions, source/target résolus).
    const nodeData: NodeDatum[] = nodes.map((n) => ({ ...n }));
    const linkData: LinkDatum[] = edges.map((e) => ({ source: e.source, target: e.target }));

    const simulation = forceSimulation<NodeDatum>(nodeData)
      .force("link", forceLink<NodeDatum, LinkDatum>(linkData).id((d) => d.id).distance(90))
      .force("charge", forceManyBody().strength(-240))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collision", forceCollide(28));

    const link = svg
      .append("g")
      .style("stroke", "var(--color-border-subtle)")
      .selectAll<SVGLineElement, LinkDatum>("line")
      .data(linkData)
      .join("line")
      .attr("stroke-width", 1.4);

    const dragHandler = drag<SVGGElement, NodeDatum>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    const node = svg
      .append("g")
      .selectAll<SVGGElement, NodeDatum>("g")
      .data(nodeData)
      .join("g")
      .style("cursor", "pointer")
      .on("click", (_event, d) => onSelect(d))
      .call(dragHandler);

    node.append("circle").attr("r", 14).style("fill", (d) => colorOf(d.type));
    node
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", 26)
      .attr("font-size", 10)
      .style("fill", "var(--color-text)")
      .text((d) => d.label);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as NodeDatum).x ?? 0)
        .attr("y1", (d) => (d.source as NodeDatum).y ?? 0)
        .attr("x2", (d) => (d.target as NodeDatum).x ?? 0)
        .attr("y2", (d) => (d.target as NodeDatum).y ?? 0);
      node.attr("transform", (d) => `translate(${d.x ?? 0}, ${d.y ?? 0})`);
    });

    return () => {
      simulation.stop();
      svg.selectAll("*").remove();
    };
  }, [nodes, edges, onSelect]);

  return <svg ref={ref} className="topology-svg" aria-label="Graphe de provenance" />;
}
