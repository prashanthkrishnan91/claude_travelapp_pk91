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

interface SearchResultCardProps {
  result: ResearchResult;
  onAdd: (result: ResearchResult) => void;
  onToggleCompare?: (result: ResearchResult) => void;
  isComparing?: boolean;
}

const categoryConfig: Record<
  ResearchCategory,
  { icon: React.ReactNode; label: string; colorClass: string; bgClass: string }
> = {
  flight: {
    icon: <Plane className="w-4 h-4" />,
    label: "Flight",
    colorClass: "text-sky-600",
    bgClass: "bg-sky-50",
  },
  hotel: {
    icon: <Hotel className="w-4 h-4" />,
    label: "Hotel",
    colorClass: "text-violet-600",
    bgClass: "bg-violet-50",
  },
  activity: {
    icon: <MapPin className="w-4 h-4" />,
    label: "Activity",
    colorClass: "text-emerald-600",
    bgClass: "bg-emerald-50",
  },
  meal: {
    icon: <Utensils className="w-4 h-4" />,
    label: "Meal",
    colorClass: "text-amber-600",
    bgClass: "bg-amber-50",
  },
  transit: {
    icon: <Train className="w-4 h-4" />,
    label: "Transit",
    colorClass: "text-slate-600",
    bgClass: "bg-slate-100",
  },
  note: {
    icon: <FileText className="w-4 h-4" />,
    label: "Note",
    colorClass: "text-rose-600",
    bgClass: "bg-rose-50",
  },
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
    <div
      ref={setNodeRef}
      style={style}
      className={`card card-lift p-3 select-none ${
        isDragging ? "opacity-50 shadow-lg scale-95" : ""
      }`}
    >
      <div className="flex items-start gap-2">
        {/* Drag handle */}
        <button
          {...listeners}
          {...attributes}
          className="mt-0.5 flex-shrink-0 cursor-grab active:cursor-grabbing text-slate-300 hover:text-slate-500 transition-colors"
          aria-label="Drag to itinerary"
        >
          <GripVertical className="w-4 h-4" />
        </button>

        {/* Category icon */}
        <div
          className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center ${config.bgClass} ${config.colorClass}`}
        >
          {config.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-1">
            <div className="flex items-center gap-1.5 min-w-0">
              <h4 className="text-sm font-semibold text-slate-800 leading-tight line-clamp-1">
                {result.title}
              </h4>
              {result.rating !== undefined && result.rating >= 4.5 && (
                <span className="badge badge-gold shrink-0 text-[10px] px-1.5 py-0.5 gap-0.5">
                  <Zap className="w-2.5 h-2.5" />
                  Top Pick
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              {onToggleCompare && (
                <button
                  onClick={() => onToggleCompare(result)}
                  className={`w-6 h-6 rounded-full flex items-center justify-center transition-colors ${
                    isComparing
                      ? "bg-violet-600 text-white"
                      : "bg-slate-100 hover:bg-violet-100 text-slate-400 hover:text-violet-600"
                  }`}
                  aria-label={isComparing ? `Remove ${result.title} from compare` : `Add ${result.title} to compare`}
                >
                  <Scale className="w-3 h-3" />
                </button>
              )}
              {result.bookingUrl && (
                <a
                  href={result.bookingUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-6 h-6 rounded-full bg-emerald-50 hover:bg-emerald-100 text-emerald-600 flex items-center justify-center transition-colors"
                  aria-label={`Book ${result.title}`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
              <button
                onClick={() => onAdd(result)}
                className="w-6 h-6 rounded-full bg-sky-600 hover:bg-sky-700 text-white flex items-center justify-center transition-colors"
                aria-label={`Add ${result.title} to itinerary`}
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {result.description && (
            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
              {result.description}
            </p>
          )}

          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            {result.location && (
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <MapPin className="w-3 h-3" />
                {result.location}
              </span>
            )}
            {result.duration && (
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Clock className="w-3 h-3" />
                {result.duration}
              </span>
            )}
            {result.rating !== undefined && (
              <span className="flex items-center gap-0.5 text-xs text-amber-500 font-medium">
                <Star className="w-3 h-3 fill-amber-500" />
                {result.rating.toFixed(1)}
              </span>
            )}
            {result.priceDisplay && (
              <span className="badge badge-value text-[10px] px-1.5 py-0.5 ml-auto">
                {result.priceDisplay}
              </span>
            )}
          </div>

          {result.category === "hotel" && typeof result.metadata?.areaLabel === "string" && (
            <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
              {(() => {
                const areaLabel = result.metadata.areaLabel as string;
                const distKm = result.metadata.distanceToBestArea as number | undefined;
                return (
                  <>
                    <span
                      className={`px-1.5 py-0.5 text-[10px] font-semibold rounded-full ${
                        areaLabel === "In Best Area"
                          ? "bg-emerald-100 text-emerald-700"
                          : areaLabel === "Close to Best Area"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {areaLabel}
                    </span>
                    {distKm != null && (
                      <span className="flex items-center gap-0.5 text-xs text-slate-400">
                        <MapPin className="w-3 h-3" />
                        {distKm < 1
                          ? `${Math.round(distKm * 1000)} m to best area`
                          : `${distKm.toFixed(1)} km to best area`}
                      </span>
                    )}
                  </>
                );
              })()}
            </div>
          )}

          {result.tags && result.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {result.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 text-xs rounded-full bg-slate-100 text-slate-500"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {(result.category === "flight" || result.category === "hotel") &&
            result.metadata?.rewardsIntelligence && (
              <RewardsIntelligencePanel
                rewards={result.metadata.rewardsIntelligence as RewardsIntelligence}
              />
            )}
        </div>
      </div>
    </div>
  );
}
