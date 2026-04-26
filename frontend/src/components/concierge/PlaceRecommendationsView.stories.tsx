import type { Meta, StoryObj } from "@storybook/react";

import { PlaceRecommendationsView } from "./PlaceRecommendationsView";

const baseResponse = {
  responseType: "place_recommendations" as const,
  response: "Here are strong options for your trip.",
  intent: "restaurants",
  retrievalUsed: true,
  sourceStatus: "live_search",
  restaurants: [],
  attractions: [],
  hotels: [],
  researchSources: [],
  areas: [],
  areaComparisons: [],
  suggestions: [],
  sources: [],
  warnings: [],
};

const meta: Meta<typeof PlaceRecommendationsView> = {
  title: "Concierge/PlaceRecommendationsView",
  component: PlaceRecommendationsView,
};

export default meta;
type Story = StoryObj<typeof PlaceRecommendationsView>;

export const RichEvidence: Story = {
  args: {
    response: {
      ...baseResponse,
      restaurants: [{ name: "Kumiko", cuisine: "Bar", evidence: ["Rated 4.7 (1,200 reviews)", "Mentioned by 3 guides", "Near West Loop"], supportingDetails: { whyPick: { text: "Kumiko stands out for rated 4.7 (1,200 reviews) and mentioned by 3 guides.", generationMethod: "deterministic" } } }],
    },
  },
};

export const SparseEvidence: Story = {
  args: {
    response: {
      ...baseResponse,
      restaurants: [{ name: "Aba", cuisine: "Restaurant", evidence: ["Rated 4.6"], supportingDetails: { whyPick: { text: "Aba is a solid choice with rated 4.6.", generationMethod: "deterministic" } } }],
    },
  },
};

export const GoogleOnlyEvidence: Story = {
  args: {
    response: {
      ...baseResponse,
      attractions: [{ name: "Cloud Gate", category: "Attraction", evidence: ["Rated 4.8 (20,121 reviews)", "Near Millennium Park"], supportingDetails: { whyPick: { text: "Cloud Gate is a solid choice with rated 4.8 (20,121 reviews).", generationMethod: "deterministic" } } }],
    },
  },
};
