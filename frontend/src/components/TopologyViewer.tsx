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
import { drag, type DragBehavior, type SubjectPosition } from "d3-drag";
import type { GraphData, GraphLink, GraphNode } from "../types";

interface TopologyViewerProps {
  graph: GraphData;
}

type NodeDatum = GraphNode & SimulationNodeDatum & { fx?: number | null; fy?: number | null };
type LinkDatum = GraphLink & SimulationLinkDatum<NodeDatum>;

export function TopologyViewer({ graph }: TopologyViewerProps) {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!ref.current || !graph.nodes.length) {
      return;
    }

    const svg = select(ref.current);
    svg.selectAll("*").remove();

    const width = ref.current.clientWidth;
    const height = ref.current.clientHeight;

    const color = (type: string) => {
      if (type === "input") return "var(--viz-1)";
      if (type === "output") return "var(--viz-2)";
      return "var(--color-text-dim)";
    };

    const simulation = forceSimulation<NodeDatum>(graph.nodes as NodeDatum[])
      .force(
        "link",
        forceLink<NodeDatum, LinkDatum>(graph.links).id((d) => String(d.id)).distance(120).strength(1)
      )
      .force("charge", forceManyBody().strength(-280))
      .force("center", forceCenter(width / 2, height / 2))
      .force("collision", forceCollide(24));

    const link = svg
      .append("g")
      .style("stroke", "var(--color-border-subtle)")
      .selectAll<SVGLineElement, LinkDatum>("line")
      .data(graph.links as LinkDatum[])
      .join("line")
      .attr("stroke-width", (d) => Math.max(1.2, Math.abs(d.weight) * 1.8));

    const dragBehavior: DragBehavior<SVGGElement, NodeDatum, NodeDatum | SubjectPosition> = drag<SVGGElement, NodeDatum>()
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

  return <svg ref={ref} className="topology-svg" aria-label="Graphe de topologie"></svg>;
}
