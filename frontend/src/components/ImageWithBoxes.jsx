import { useState } from "react";

// Draws YOLO boxes (pixel coordinates of the ORIGINAL image) over the preview using an SVG viewBox,
// so the boxes stay aligned however the image is scaled on screen.
export default function ImageWithBoxes({ src, boxes }) {
  const [size, setSize] = useState(null);
  return (
    <div className="imgwrap">
      <img src={src} alt="Uploaded crop" onLoad={(e) => setSize({ w: e.target.naturalWidth, h: e.target.naturalHeight })} />
      {size && (
        <svg viewBox={`0 0 ${size.w} ${size.h}`} preserveAspectRatio="none">
          {boxes.map((b, i) => {
            const [x1, y1, x2, y2] = b.bbox_xyxy;
            const stroke = Math.max(size.w, size.h) / 200;
            return (
              <g key={i}>
                <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke="red" strokeWidth={stroke} />
                <text x={x1 + stroke} y={Math.max(y1 - stroke, stroke * 6)} fill="red" fontSize={stroke * 7}>
                  {b.pest} {b.confidence}%
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
