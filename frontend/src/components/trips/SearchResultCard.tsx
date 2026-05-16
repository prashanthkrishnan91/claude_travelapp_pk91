"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import {
  Plane,
  Hotel,
  MapPin,
  Utensils,
  Train,
  FileText,
  Star,
  GripVertical,
  Plus,
  Clock,
  Scale,
  ExternalLink,
  Zap,
} from "lucide-react";
import { ResearchResult, ResearchCategory, RewardsIntelligence } from "@/types";
import { RewardsIntelligencePanel } from "./RewardsIntelligencePanel";
import { Card } from "@/components/ui/Card";

interface SearchResultCardProps {
  result: ResearchResult;
  onAdd: (result: ResearchResult) => void;
  onToggleCompare?: (result: ResearchResult) => void;
  isComparing?: boolean;
}

const categoryConfig: Record<ResearchCategory, { icon: React.ReactNode; label: string }> = {
  flight:  { icon: <Plane className="w-4 h-4" />,    label: "Flight" },
  hotel:   { icon: <Hotel className="w-4 h-4" />,    label: "Hotel" },
  activity:{ icon: <MapPin className="w-4 h-4" />,   label: "Activity" },
  meal:    { icon: <Utensils className="w-4 h-4" />, label: "Meal" },
  transit: { icon: <Train className="w-4 h-4" />,    label: "Transit" },
  note:    { icon: <FileText className="w-4 h-4" />, label: "Note" },
};

export function SearchResultCard({ result, onAdd, onToggleCompare, isComparing }: SearchResultCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id: `result-${result.id}`,
      data: { type: "result", result },
    });

  const style = transform
    ? { transform: CSS.Translate.toString(transform) }
    : undefined;

  const config = categoryConfig[result.category];

  return (
    <div ref={setNodeRef} style={style}>
    <Card
      tone="dark"
      as="article"
      className={`card-lift p-3 select-none ${isDragging ? "opacity-50 shadow-lg scale-95" : ""}`}
    >
      <Card.Identity>
        {/* Drag handle — -m-3.5 p-3.5 yields 44px hit area (16px icon + 14px*2 padding) */}
        <button
          {...listeners}
          {...attributes}
          className="mt-0.5 flex-shrink-0 -m-3.5 p-3.5 flex items-center justify-center cursor-grab active:cursor-grabbing text-ds-text-tertiary hover:text-ds-text-secondary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          aria-label="Drag to itinerary"
        >
          <GripVertical className="w-4 h-4" />
        </button>

        {/* Category icon */}
        <div
          className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-ds-accent"
          style={{ backgroundColor: "var(--ds-accent-subtle)" }}
          aria-hidden="true"
        >
          {config.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-1">
            <div className="flex items-center gap-1.5 min-w-0">
              <h4 className="text-sm font-semibold text-ds-text leading-tight line-clamp-1">
                {result.title}
              </h4>
              {result.rating !== undefined && result.rating >= 4.5 && (
                <span className="badge badge-gold shrink-0 text-[10px] px-1.5 py-0.5 gap-0.5">
                  <Zap className="w-2.5 h-2.5" />
                  Top Pick
                </span>
              )}
            </div>
            {/* Each button uses -m-2.5 p-2.5: 24px visual + 10px*2 padding = 44px hit area */}
            <div className="flex items-center gap-1 flex-shrink-0">
              {onToggleCompare && (
                <button
                  onClick={() => onToggleCompare(result)}
                  className="group -m-2.5 p-2.5 flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  aria-label={isComparing ? `Remove ${result.title} from compare` : `Add ${result.title} to compare`}
                >
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center transition-colors ${
                    isComparing
                      ? "bg-ds-accent text-ds-text-inverse"
                      : "bg-ds-carbon text-ds-text-tertiary group-hover:text-ds-accent"
                  }`}>
                    <Scale className="w-3 h-3" />
                  </span>
                </button>
              )}
              {result.bookingUrl && (
                <a
                  href={result.bookingUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group -m-2.5 p-2.5 flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  aria-label={`Book ${result.title}`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <span className="w-6 h-6 rounded-full bg-ds-carbon group-hover:bg-ds-pen-stroke text-ds-text-tertiary group-hover:text-ds-text-secondary flex items-center justify-center transition-colors">
                    <ExternalLink className="w-3 h-3" />
                  </span>
                </a>
              )}
              <button
                onClick={() => onAdd(result)}
                className="group -m-2.5 p-2.5 flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                aria-label={`Add ${result.title} to itinerary`}
              >
                <span className="w-6 h-6 rounded-full bg-ds-accent group-hover:bg-ds-accent-muted text-ds-text-inverse flex items-center justify-center transition-colors">
                  <Plus className="w-3.5 h-3.5" />
                </span>
              </button>
            </div>
          </div>

          {result.description && (
            <p className="text-xs text-ds-text-tertiary mt-0.5 line-clamp-2">
              {result.description}
            </p>
          )}
        </div>
      </Card.Identity>

      <Card.Meta className="mt-1.5">
        {result.location && (
          <span className="flex items-center gap-1 text-xs text-ds-text-tertiary">
            <MapPin className="w-3 h-3" />
            {result.location}
          </span>
        )}
        {result.duration && (
          <span className="flex items-center gap-1 text-xs text-ds-text-tertiary">
            <Clock className="w-3 h-3" />
            {result.duration}
          </span>
        )}
        {result.rating !== undefined && (
          <span className="flex items-center gap-0.5 text-xs text-ds-accent font-medium">
            <Star className="w-3 h-3 fill-current" />
            {result.rating.toFixed(1)}
          </span>
        )}
        {result.priceDisplay && (
          <span className="badge badge-value text-[10px] px-1.5 py-0.5 ml-auto">
            {result.priceDisplay}
          </span>
        )}
      </Card.Meta>

      {result.category === "hotel" && typeof result.metadata?.areaLabel === "string" && (
        <Card.Meta className="mt-1.5">
          {(() => {
            const areaLabel = result.metadata.areaLabel as string;
            const distKm = result.metadata.distanceToBestArea as number | undefined;
            return (
              <>
                <span
                  className={`px-1.5 py-0.5 text-[10px] font-semibold rounded-full border ${
                    areaLabel === "In Best Area"
                      ? "text-ds-trust-verified border-ds-trust-verified/30"
                      : areaLabel === "Close to Best Area"
                        ? "text-ds-caution border-ds-caution/30"
                        : "bg-ds-carbon text-ds-text-tertiary border-ds-pen-stroke"
                  }`}
                >
                  {areaLabel}
                </span>
                {distKm != null && (
                  <span className="flex items-center gap-0.5 text-xs text-ds-text-tertiary">
                    <MapPin className="w-3 h-3" />
                    {distKm < 1
                      ? `${Math.round(distKm * 1000)} m to best area`
                      : `${distKm.toFixed(1)} km to best area`}
                  </span>
                )}
              </>
            );
          })()}
        </Card.Meta>
      )}

      {result.tags && result.tags.length > 0 && (
        <Card.Meta className="mt-1.5">
          {result.tags.map((tag) => (
            <span
              key={tag}
              className="px-1.5 py-0.5 text-xs rounded-full bg-ds-carbon text-ds-text-tertiary border border-ds-pen-stroke"
            >
              {tag}
            </span>
          ))}
        </Card.Meta>
      )}

      {(result.category === "flight" || result.category === "hotel") &&
        !!result.metadata?.rewardsIntelligence && (
          <RewardsIntelligencePanel
            rewards={result.metadata.rewardsIntelligence as RewardsIntelligence}
          />
        )}
    </Card>
    </div>
  );
}
