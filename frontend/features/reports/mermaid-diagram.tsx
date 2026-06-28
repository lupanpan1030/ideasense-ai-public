"use client";

import { useId, useMemo } from "react";

type MermaidDiagramProps = {
  code: string;
};

type MermaidNode = {
  id: string;
  label: string;
};

type MermaidEdge = {
  from: string;
  to: string;
};

type MermaidLayout = {
  nodes: MermaidNode[];
  edges: MermaidEdge[];
  positions: Record<string, { x: number; y: number }>;
  width: number;
  height: number;
  nodeWidth: number;
  nodeHeight: number;
  isHorizontal: boolean;
};

const NODE_RE = /^([A-Za-z0-9_-]+)\s*(\[(.+?)\]|\((.+?)\)|\{(.+?)\})?/;

const parseNodeToken = (token: string): MermaidNode | null => {
  const cleaned = token.split(":::")[0].trim();
  if (!cleaned) {
    return null;
  }
  const match = cleaned.match(NODE_RE);
  if (!match) {
    return { id: cleaned, label: cleaned };
  }
  const label = match[3] ?? match[4] ?? match[5] ?? match[1];
  return { id: match[1], label };
};

const buildLayout = (code: string): MermaidLayout => {
  const lines = code
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  let direction = "TD";
  const nodes = new Map<string, MermaidNode>();
  const edges: MermaidEdge[] = [];

  const addNode = (node: MermaidNode | null) => {
    if (!node) {
      return;
    }
    const existing = nodes.get(node.id);
    if (!existing) {
      nodes.set(node.id, node);
    } else if (existing.label === existing.id && node.label !== node.id) {
      nodes.set(node.id, node);
    }
  };

  for (const line of lines) {
    if (line.startsWith("%%") || line.startsWith("%%{")) {
      continue;
    }
    if (line.startsWith("graph") || line.startsWith("flowchart")) {
      const parts = line.split(/\s+/);
      if (parts[1]) {
        direction = parts[1].toUpperCase();
      }
      continue;
    }
    if (
      line.startsWith("subgraph") ||
      line.startsWith("end") ||
      line.startsWith("classDef") ||
      line.startsWith("class ") ||
      line.startsWith("style ")
    ) {
      continue;
    }

    if (line.includes("-->")) {
      const segments = line.split("-->").map((segment) => segment.split("--")[0].trim());
      for (let index = 0; index < segments.length - 1; index += 1) {
        const leftNode = parseNodeToken(segments[index]);
        const rightNode = parseNodeToken(segments[index + 1]);
        addNode(leftNode);
        addNode(rightNode);
        if (leftNode && rightNode) {
          edges.push({ from: leftNode.id, to: rightNode.id });
        }
      }
      continue;
    }

    const nodeOnly = parseNodeToken(line);
    addNode(nodeOnly);
  }

  const nodeList = Array.from(nodes.values());
  const maxLabelLength = nodeList.reduce(
    (max, node) => Math.max(max, node.label.length),
    4
  );
  const nodeWidth = Math.min(320, Math.max(160, maxLabelLength * 7 + 32));
  const nodeHeight = 56;
  const gapX = 56;
  const gapY = 32;
  const padding = 24;
  const isHorizontal = ["LR", "RL"].includes(direction.toUpperCase());

  const positions: Record<string, { x: number; y: number }> = {};
  nodeList.forEach((node, index) => {
    const x = isHorizontal
      ? padding + index * (nodeWidth + gapX)
      : padding;
    const y = isHorizontal
      ? padding
      : padding + index * (nodeHeight + gapY);
    positions[node.id] = { x, y };
  });

  const width = isHorizontal
    ? padding * 2 + nodeList.length * nodeWidth + Math.max(0, nodeList.length - 1) * gapX
    : nodeWidth + padding * 2;
  const height = isHorizontal
    ? nodeHeight + padding * 2
    : padding * 2 + nodeList.length * nodeHeight + Math.max(0, nodeList.length - 1) * gapY;

  return {
    nodes: nodeList,
    edges,
    positions,
    width: Math.max(width, 220),
    height: Math.max(height, 140),
    nodeWidth,
    nodeHeight,
    isHorizontal,
  };
};

export function MermaidDiagram({ code }: MermaidDiagramProps) {
  const markerId = useId().replace(/:/g, "");
  const layout = useMemo(() => buildLayout(code), [code]);

  if (!layout.nodes.length) {
    const lines = code
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(0, 10);
    return (
      <div className="mermaid-diagram" aria-label="Architecture diagram">
        <svg
          viewBox="0 0 480 200"
          role="img"
          aria-label="Architecture diagram"
        >
          {lines.map((line, index) => (
            <text
              key={`fallback-line-${index}`}
              x={16}
              y={28 + index * 16}
              className="mermaid-fallback"
            >
              {line}
            </text>
          ))}
        </svg>
      </div>
    );
  }

  return (
    <div className="mermaid-diagram" aria-label="Architecture diagram">
      <svg
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        width={layout.width}
        height={layout.height}
        role="img"
        aria-label="Architecture diagram"
      >
        <defs>
          <marker
            id={`arrow-${markerId}`}
            markerWidth="10"
            markerHeight="10"
            refX="10"
            refY="5"
            orient="auto"
          >
            <path d="M0 0 L10 5 L0 10 Z" className="mermaid-arrow" />
          </marker>
        </defs>
        {layout.edges.map((edge, index) => {
          const from = layout.positions[edge.from];
          const to = layout.positions[edge.to];
          if (!from || !to) {
            return null;
          }
          const x1 = layout.isHorizontal
            ? from.x + layout.nodeWidth
            : from.x + layout.nodeWidth / 2;
          const y1 = layout.isHorizontal
            ? from.y + layout.nodeHeight / 2
            : from.y + layout.nodeHeight;
          const x2 = layout.isHorizontal
            ? to.x
            : to.x + layout.nodeWidth / 2;
          const y2 = layout.isHorizontal
            ? to.y + layout.nodeHeight / 2
            : to.y;
          return (
            <path
              key={`edge-${edge.from}-${edge.to}-${index}`}
              d={`M ${x1} ${y1} L ${x2} ${y2}`}
              className="mermaid-edge"
              markerEnd={`url(#arrow-${markerId})`}
            />
          );
        })}
        {layout.nodes.map((node) => {
          const position = layout.positions[node.id];
          if (!position) {
            return null;
          }
          const textX = position.x + layout.nodeWidth / 2;
          const textY = position.y + layout.nodeHeight / 2 + 5;
          return (
            <g key={`node-${node.id}`} className="mermaid-node">
              <rect
                x={position.x}
                y={position.y}
                rx={12}
                ry={12}
                width={layout.nodeWidth}
                height={layout.nodeHeight}
              />
              <text x={textX} y={textY} textAnchor="middle">
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
