"use client";

import { useState } from "react";
import { Search, MapPin, Phone, CheckCircle2, Loader2 } from "lucide-react";
import { labApi } from "../../lib/api";
import { Lab } from "../../lib/types";

export default function LabFinder() {
  const [query, setQuery] = useState("");
  const [pincode, setPincode] = useState("");
  const [labs, setLabs] = useState<Lab[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    const res = await labApi.searchLabs(query, pincode || undefined);
    if (res.success) {
      setLabs(res.data);
    } else {
      setError(res.error ?? "Search failed");
    }
    setLoading(false);
    setSearched(true);
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search labs by name or service..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-gov-navy transition"
          />
        </div>
        <input
          value={pincode}
          onChange={(e) => setPincode(e.target.value)}
          placeholder="Pincode (optional)"
          maxLength={6}
          className="w-36 px-4 py-2.5 rounded-xl border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-gov-navy transition"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-6 py-2.5 rounded-xl bg-gov-navy text-white text-sm font-medium hover:bg-gov-navy/90 disabled:opacity-40 transition flex items-center gap-2"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          Search
        </button>
      </form>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {searched && labs.length === 0 && !loading && (
        <p className="text-center text-sm text-muted-foreground py-8">
          No labs found. Try a different search term.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {labs.map((lab) => (
          <div
            key={lab.id}
            className="rounded-xl border border-border bg-card p-4 space-y-3 hover:border-gov-navy/40 hover:shadow-sm transition"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold text-foreground text-sm">{lab.name}</h3>
              {lab.accredited && (
                <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="h-3 w-3" />
                  Accredited
                </span>
              )}
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex items-start gap-1.5">
                <MapPin className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-gov-orange" />
                <span>{lab.address}, {lab.city}, {lab.state} - {lab.pincode}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5 flex-shrink-0 text-gov-orange" />
                <a href={`tel:${lab.phone}`} className="hover:text-gov-navy transition">{lab.phone}</a>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {lab.services.slice(0, 3).map((s) => (
                <span key={s} className="text-xs bg-gov-navy/10 text-gov-navy px-2 py-0.5 rounded-full">
                  {s}
                </span>
              ))}
              {lab.services.length > 3 && (
                <span className="text-xs text-muted-foreground">+{lab.services.length - 3} more</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}