import type { ProjectVerificationSnapshot } from "@/features/assessments/api";
import type { ReportSnapshot } from "./reports-normalize";

export const buildSampleVerificationSnapshot = (
  source: ReportSnapshot | null
): ProjectVerificationSnapshot | null => {
  if (!source) {
    return null;
  }

  return {
    projectId: source.projectId,
    stages: source.assessments.map((assessment) => {
      const stage = assessment.stage;
      const supportedEntries = assessment.contextCard.userConfirmedInputs;
      const uncertainEntries = [
        ...assessment.contextCard.founderAssumptions.map((entry, index) => ({
          id: `${entry.path ?? entry.label}-assumption-${index}`,
          path: entry.path,
          label: entry.label,
          value: entry.value,
        })),
        ...assessment.contextCard.evidenceGaps.map((gap, index) => ({
          id: `${gap.path ?? gap.label}-gap-${index}`,
          path: gap.path,
          label: gap.label,
          value: gap.reason,
        })),
      ];
      const questions = [
        ...supportedEntries.map((entry, index) => ({
          questionId: entry.path ?? `${stage}-supported-${index}`,
          questionTitle: entry.label,
          priority: "high",
          status: "supported",
          statusDetail: entry.evidenceLevel,
          supportedClaims: 1,
          contradictedClaims: 0,
          uncertainClaims: 0,
          totalClaims: 1,
          sources: [
            {
              title: "Sample workspace evidence",
              url: null,
              domain: "Sample data",
              snippet: entry.value,
            },
          ],
        })),
        ...uncertainEntries.map((entry, index) => ({
          questionId: entry.id || entry.path || `${stage}-uncertain-${index}`,
          questionTitle: entry.label,
          priority: "medium",
          status: "uncertain",
          statusDetail: "Needs direct validation",
          supportedClaims: 0,
          contradictedClaims: 0,
          uncertainClaims: 1,
          totalClaims: 1,
          sources: [
            {
              title: "Sample workspace evidence",
              url: null,
              domain: "Sample data",
              snippet: entry.value,
            },
          ],
        })),
      ];
      const supported = supportedEntries.length;
      const uncertain = uncertainEntries.length;

      return {
        stage,
        total: questions.length,
        supported,
        contradicted: 0,
        uncertain,
        failed: 0,
        stale: 0,
        providerUnavailable: 0,
        notChecked: 0,
        verified: supported,
        verifying: 0,
        noEvidence: 0,
        notApplicable: 0,
        questions,
      };
    }),
  };
};
