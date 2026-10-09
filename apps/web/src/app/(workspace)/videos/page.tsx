"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Clapperboard, Play, Plus } from "lucide-react";
import { api, type Video } from "@/lib/api";
import { Empty, ErrorNote, Loading } from "@/components/states";
import { Badge, PageHeader } from "@/components/ui";

function tone(status: string): "success" | "warning" | "danger" | "info" | "neutral" {
  if (status === "ready") return "success";
  if (status === "failed") return "danger";
  if (status === "processing") return "warning";
  return "info";
}

export default function VideosPage() {
  const videos = useQuery({ queryKey: ["videos"], queryFn: () => api<{ items: Video[]; total: number }>("/videos") });
  if (videos.isLoading) return <Loading />;
  if (videos.isError) return <ErrorNote error={videos.error} />;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Library"
        title="Videos"
        description="Every clip keeps its processing state in the open. Ready means a signed playback link exists."
        actions={
          <Link href="/videos/upload" className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-4 py-2 text-sm font-semibold text-[#04121a] shadow-[0_8px_32px_-8px_rgb(0_212_255/0.5)] transition-all hover:brightness-110 active:scale-[0.97]">
            <Plus size={15} /> Upload
          </Link>
        }
      />
      {videos.data?.items.length ? (
        <ul className="grid gap-3 md:grid-cols-2">
          {videos.data.items.map((video, index) => (
            <li key={video.id}>
              <Link
                href={`/videos/${video.id}`}
                className="fi-rise group flex items-center gap-4 rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.055] to-white/[0.015] p-4 transition-all duration-150 hover:border-white/20 active:scale-[0.99]"
                style={{ animationDelay: `${Math.min(index, 6) * 50}ms` }}
              >
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-secondary/30 text-primary transition-transform duration-150 group-hover:scale-105">
                  {video.status === "processing" ? <Clapperboard size={19} className="animate-pulse" /> : <Play size={19} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{video.title}</span>
                  <span className="mt-1.5 flex items-center gap-2 text-xs text-muted">
                    <Badge tone={tone(video.status)}>
                      {video.status === "processing" ? (
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                      ) : null}
                      {video.status}
                    </Badge>
                    {video.weapon}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <Empty>No videos yet. Upload a fencing bout to review it.</Empty>
      )}
    </div>
  );
}
