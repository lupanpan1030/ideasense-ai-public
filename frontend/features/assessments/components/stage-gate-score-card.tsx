"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { StageScoreSummary } from "../api";
import { formatScore } from "./stage-gate-utils";

type StageGateScoreCardProps = {
  nextStageLabel: string;
  totalScore: number | null;
  scoreSummary: StageScoreSummary | null;
};

export function StageGateScoreCard({
  nextStageLabel,
  totalScore,
  scoreSummary,
}: StageGateScoreCardProps) {
  return (
    <Card>
      <CardHeader className="stack-sm">
        <div className="cluster-tight">
          <CardTitle>Confirmation complete</CardTitle>
          <Badge variant="success">Computed</Badge>
        </div>
        <CardDescription>Stage advanced to {nextStageLabel}.</CardDescription>
      </CardHeader>
      <CardContent className="stack-sm">
        <div className="cluster">
          <Badge variant="info">Total</Badge>
          <span className="stat-value">{formatScore(totalScore)}</span>
        </div>
        <Separator />
        <div className="stack-sm">
          <div className="cluster">
            <Badge>Desirability</Badge>
            <span>{formatScore(scoreSummary?.desirability ?? null)}</span>
          </div>
          <div className="cluster">
            <Badge>Viability</Badge>
            <span>{formatScore(scoreSummary?.viability ?? null)}</span>
          </div>
          <div className="cluster">
            <Badge>Feasibility</Badge>
            <span>{formatScore(scoreSummary?.feasibility ?? null)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
