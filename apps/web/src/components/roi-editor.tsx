"use client";

import { useEffect, useState } from "react";
import { Image as KonvaImage, Layer, Rect, Stage } from "react-konva";
import { api } from "@/lib/api";
import { buttonClass } from "./states";

export function RoiEditor({ videoId, width, height, posterUrl }: { videoId: string; width: number; height: number; posterUrl: string | null }) {
  const [rect, setRect] = useState({ x: 40, y: 20, w: 120, h: 50 });
  const [saved, setSaved] = useState("");
  const [frame, setFrame] = useState<HTMLImageElement | null>(null);
  const [frameFailed, setFrameFailed] = useState(false);
  const scale = Math.min(1, 640 / width);
  const stageW = Math.round(width * scale);
  const stageH = Math.round(height * scale);

  useEffect(() => {
    setFrame(null);
    setFrameFailed(false);
    if (!posterUrl) return;
    const img = new window.Image();
    // No crossOrigin: the frame is only displayed, never read back, so the
    // bucket CORS allowlist does not need the web origin for this to render.
    img.onload = () => setFrame(img);
    img.onerror = () => setFrameFailed(true);
    img.src = posterUrl;
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [posterUrl]);

  const clamp = (x: number, y: number) => ({
    x: Math.min(Math.max(0, Math.round(x)), Math.max(0, stageW - rect.w)),
    y: Math.min(Math.max(0, Math.round(y)), Math.max(0, stageH - rect.h)),
  });

  return (
    <div className="grid gap-2">
      <p className="text-sm text-muted">Drag the rectangle onto the scoreboard, then save the region. Lights found there become candidates, not referee calls.</p>
      <div className="mx-auto w-fit rounded-xl bg-black p-2">
        <Stage width={stageW} height={stageH}>
          <Layer>
            {frame ? <KonvaImage image={frame} width={stageW} height={stageH} listening={false} /> : null}
            <Rect
              x={rect.x}
              y={rect.y}
              width={rect.w}
              height={rect.h}
              stroke="#00d4ff"
              dash={[4, 4]}
              draggable
              onDragEnd={(event) => {
                const next = clamp(event.target.x(), event.target.y());
                event.target.position(next);
                setRect({ ...rect, ...next });
              }}
            />
          </Layer>
        </Stage>
      </div>
      {!posterUrl || frameFailed ? (
        <p className="text-sm text-muted">
          {frameFailed
            ? "The preview frame could not load. You can still save the region, but place it after checking the video below."
            : "No preview frame yet. The region saves against normalized coordinates once a frame loads."}
        </p>
      ) : null}
      <button
        type="button"
        className={buttonClass}
        onClick={async () => {
          await api(`/videos/${videoId}/scoreboard-roi`, {
            method: "PUT",
            body: JSON.stringify({
              x: rect.x / stageW,
              y: rect.y / stageH,
              w: rect.w / stageW,
              h: rect.h / stageH,
            }),
          });
          setSaved("Region saved");
        }}
      >
        Save scoreboard region
      </button>
      {saved ? <p className="text-sm text-success">{saved}</p> : null}
    </div>
  );
}
