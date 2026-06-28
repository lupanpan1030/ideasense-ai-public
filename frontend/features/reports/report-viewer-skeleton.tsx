import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function ReportViewerSkeleton() {
  return (
    <div className="report-doc" aria-live="polite">
      <section className="report-section">
        <div className="report-section__header">
          <div className="stack-sm">
            <div aria-hidden="true" className="skeleton skeleton--line" />
            <div aria-hidden="true" className="skeleton skeleton--title" />
            <div aria-hidden="true" className="skeleton skeleton--line" />
          </div>
        </div>
        <Card className="report-panel">
          <CardHeader>
            <div className="card__title">
              <div aria-hidden="true" className="skeleton skeleton--title" />
            </div>
          </CardHeader>
          <CardContent className="stack-sm">
            <div aria-hidden="true" className="skeleton skeleton--line" />
            <div aria-hidden="true" className="skeleton skeleton--line" />
            <div aria-hidden="true" className="skeleton skeleton--line" />
          </CardContent>
        </Card>
        <div className="report-score-stack">
          {Array.from({ length: 2 }).map((_, index) => (
            <Card key={`report-skeleton-score-${index}`} className="report-panel">
              <CardHeader>
                <div className="card__title">
                  <div aria-hidden="true" className="skeleton skeleton--title" />
                </div>
              </CardHeader>
              <CardContent className="stack-sm">
                <div aria-hidden="true" className="skeleton skeleton--line" />
                <div aria-hidden="true" className="skeleton skeleton--line" />
                <div aria-hidden="true" className="skeleton skeleton--line" />
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {Array.from({ length: 3 }).map((_, index) => (
        <section key={`report-skeleton-section-${index}`} className="report-section">
          <div className="report-section__header">
            <div className="stack-sm">
              <div aria-hidden="true" className="skeleton skeleton--line" />
              <div aria-hidden="true" className="skeleton skeleton--title" />
              <div aria-hidden="true" className="skeleton skeleton--line" />
            </div>
          </div>
          <Card className="report-panel">
            <CardHeader>
              <div className="card__title">
                <div aria-hidden="true" className="skeleton skeleton--title" />
              </div>
            </CardHeader>
            <CardContent className="stack-sm">
              <div aria-hidden="true" className="skeleton skeleton--line" />
              <div aria-hidden="true" className="skeleton skeleton--line" />
              <div aria-hidden="true" className="skeleton skeleton--line" />
            </CardContent>
          </Card>
        </section>
      ))}
    </div>
  );
}
