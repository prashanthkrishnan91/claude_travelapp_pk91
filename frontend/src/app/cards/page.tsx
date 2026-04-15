import type { Metadata } from "next";
import { CreditCard, PlusCircle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";

export const metadata: Metadata = { title: "Travel Cards" };

export default function CardsPage() {
  return (
    <>
      <PageHeader
        title="Travel Cards"
        description="Manage your credit cards and track points balances."
        action={
          <button className="btn-primary">
            <PlusCircle className="w-4 h-4" />
            Add Card
          </button>
        }
      />
      <div className="card">
        <EmptyState
          icon={<CreditCard className="w-6 h-6" />}
          title="No cards added yet"
          description="Add your travel credit cards to track points and get personalized redemption recommendations."
          action={
            <button className="btn-primary">
              <PlusCircle className="w-4 h-4" />
              Add Card
            </button>
          }
        />
      </div>
    </>
  );
}
