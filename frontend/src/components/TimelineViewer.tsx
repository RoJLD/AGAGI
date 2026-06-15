import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { queryKeys } from "../api/queryKeys";
import { Loading } from "./ui/Loading";
import { ErrorState } from "./ui/ErrorState";
import { Empty } from "./ui/Empty";

export function TimelineViewer() {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.timeline,
    queryFn: () => apiFetch<{ nodes: any[]; links: any[] }>("/api/timeline"),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (!data || !svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 800;
    const height = 400;

    const simulation = d3
      .forceSimulation(data.nodes)
      .force(
        "link",
        d3.forceLink(data.links).id((d: any) => d.id).distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg
      .append("g")
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2);

    const node = svg
      .append("g")
      .selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", 10)
      .attr("fill", (d: any) => d.label === "Agent" ? "#be123c" : "#0f766e");

    const label = svg
      .append("g")
      .selectAll("text")
      .data(data.nodes)
      .join("text")
      .text((d: any) => d.id)
      .attr("font-size", 10)
      .attr("dx", 12)
      .attr("dy", 4);

    node.append("title").text((d: any) => `${d.label}: ${d.id}`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("cx", (d: any) => d.x)
        .attr("cy", (d: any) => d.y);

      label
        .attr("x", (d: any) => d.x)
        .attr("y", (d: any) => d.y);
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
