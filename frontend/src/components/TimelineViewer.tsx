import { useEffect, useRef } from "react";
import { select } from "d3-selection";
import {
  forceSimulation,
  forceCenter,
  forceLink,
  forceManyBody,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";

type TimelineNode = { id: string; label: string } & SimulationNodeDatum;
type TimelineLink = SimulationLinkDatum<TimelineNode>;

export function TimelineViewer() {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.timeline,
    queryFn: () => apiFetch<{ nodes: TimelineNode[]; links: TimelineLink[] }>("/api/timeline"),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const svg = select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 800;
    const height = 400;

    const simulation = forceSimulation<TimelineNode>(data.nodes)
      .force(
        "link",
        forceLink<TimelineNode, TimelineLink>(data.links).id((d) => d.id).distance(100),
      )
      .force("charge", forceManyBody().strength(-300))
      .force("center", forceCenter(width / 2, height / 2));

    const link = svg
      .append("g")
      .selectAll<SVGLineElement, TimelineLink>("line")
      .data(data.links)
      .join("line")
      .style("stroke", "var(--color-border)")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2);

    const node = svg
      .append("g")
      .selectAll<SVGCircleElement, TimelineNode>("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", 10)
      // Séries data-viz -> tokens theme-aware (rouge = Agent, teal = autre).
      .style("fill", (d) => (d.label === "Agent" ? "var(--viz-2)" : "var(--viz-1)"));

    const label = svg
      .append("g")
      .selectAll<SVGTextElement, TimelineNode>("text")
      .data(data.nodes)
      .join("text")
      .text((d) => d.id)
      .attr("font-size", 10)
      .attr("dx", 12)
      .attr("dy", 4)
      .style("fill", "var(--color-text)"); // sinon noir par défaut -> invisible en dark

    // `append("title")` ne propage pas le datum générique : on re-cast vers TimelineNode.
    node.append("title").text((d) => `${(d as TimelineNode).label}: ${(d as TimelineNode).id}`);

    simulation.on("tick", () => {
      // d3.SimulationLinkDatum.source/target est typé `string | number | TimelineNode` ;
      // après initialisation de la simulation, d3 les résout en nœuds -> cast vers TimelineNode.
      link
        .attr("x1", (d) => (d.source as TimelineNode).x ?? 0)
        .attr("y1", (d) => (d.source as TimelineNode).y ?? 0)
        .attr("x2", (d) => (d.target as TimelineNode).x ?? 0)
        .attr("y2", (d) => (d.target as TimelineNode).y ?? 0);

      node.attr("cx", (d) => d.x ?? 0).attr("cy", (d) => d.y ?? 0);
      label.attr("x", (d) => d.x ?? 0).attr("y", (d) => d.y ?? 0);
    });

    return () => {
      simulation.stop();
    };
  }, [data]);

  if (isLoading) return <Loading label="Chargement du graphe KuzuDB…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || !data.nodes?.length) return <Empty message="Aucun nœud dans le graphe KuzuDB." />;

  return (
    <div className="timeline-viewer">
      <h2>Timeline KuzuDB</h2>
      <p>Visualisation de l'arbre généalogique des agents et de leurs lignées.</p>
      <svg ref={svgRef} width="100%" height={400} className="topology-svg" />
    </div>
  );
}
