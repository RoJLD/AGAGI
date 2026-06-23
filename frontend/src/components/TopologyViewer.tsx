import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { GraphData, GraphLink, GraphNode } from "../types";

interface TopologyViewerProps {
  graph: GraphData;
}

type NodeDatum = GraphNode & d3.SimulationNodeDatum & { fx?: number | null; fy?: number | null };
type LinkDatum = GraphLink & d3.SimulationLinkDatum<NodeDatum>;

export function TopologyViewer({ graph }: TopologyViewerProps) {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!ref.current || !graph.nodes.length) {
      return;
    }

    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();

    const width = ref.current.clientWidth;
    const height = ref.current.clientHeight;

    const color = (type: string) => {
      if (type === "input") return "var(--viz-1)";
      if (type === "output") return "var(--viz-2)";
      return "var(--color-text-dim)";
    };

    const simulation = d3
      .forceSimulation<NodeDatum>(graph.nodes as NodeDatum[])
      .force(
        "link",
        d3.forceLink<NodeDatum, LinkDatum>(graph.links).id((d) => d.id as any).distance(120).strength(1)
      )
      .force("charge", d3.forceManyBody().strength(-280))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(24));

    const link = svg
      .append("g")
      .style("stroke", "var(--color-border-subtle)")
      .selectAll<SVGLineElement, LinkDatum>("line")
      .data(graph.links as LinkDatum[])
      .join("line")
      .attr("stroke-width", (d) => Math.max(1.2, Math.abs(d.weight) * 1.8));

    const dragBehavior = d3
      .drag<SVGGElement, NodeDatum>()
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
      }) as any;

    const node = svg
      .append("g")
      .selectAll<SVGGElement, NodeDatum>("g")
      .data(graph.nodes as NodeDatum[])
      .join("g")
      .call(dragBehavior);

    node
      .append("circle")
      .attr("r", 18)
      .style("fill", (d: NodeDatum) => color(d.type));

    node
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", 4)
      .attr("font-size", 11)
      // Token « texte sur surface colorée » : bascule white (clair) -> sombre (dark) pour
      // rester contrasté sur les cercles --viz-* qui s'éclaircissent en thème sombre.
      // `.style` (et non `.attr`) car var() n'est pas résolu dans un attribut SVG.
      .style("fill", "var(--color-on-accent)")
      .text((d: NodeDatum) => d.label);

    simulation.on("tick", () => {
      link
        .attr("x1", (d: LinkDatum) => (d.source as NodeDatum).x!)
        .attr("y1", (d: LinkDatum) => (d.source as NodeDatum).y!)
        .attr("x2", (d: LinkDatum) => (d.target as NodeDatum).x!)
        .attr("y2", (d: LinkDatum) => (d.target as NodeDatum).y!);

      node.attr("transform", (d: NodeDatum) => `translate(${d.x}, ${d.y})`);
    });

    return () => {
      simulation.stop();
      svg.selectAll("*").remove();
    };
  }, [graph]);

  return <svg ref={ref} className="topology-svg" aria-label="Topology graph"></svg>;
}
