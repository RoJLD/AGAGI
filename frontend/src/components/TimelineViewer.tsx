import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

export function TimelineViewer() {
  const [data, setData] = useState<{ nodes: any[]; links: any[] } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/timeline`)
      .then((res) => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

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

  return (
    <div className="timeline-viewer">
      <h2>Timeline KuzuDB</h2>
      <p>Visualisation de l'arbre généalogique des agents et de leurs lignées.</p>
      {data ? (
        <svg ref={svgRef} width="100%" height={400} style={{ border: "1px solid #ccc", background: "#f8f9fa" }} />
      ) : (
        <p>Chargement des données du graphe...</p>
      )}
    </div>
  );
}
