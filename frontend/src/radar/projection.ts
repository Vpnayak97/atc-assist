export interface View { cx: number; cy: number; pxPerNm: number; rangeNm: number; w: number; h: number }

export function makeView(w: number, h: number, rangeNm: number): View {
  const r = Math.min(w, h) / 2 - 30
  return { cx: w / 2, cy: h / 2, pxPerNm: r / rangeNm, rangeNm, w, h }
}

// x = nm east, y = nm north of the airport (the backend projects; see geo.to_xy_nm)
export const toScreen = (v: View, x: number, y: number): [number, number] => [v.cx + x * v.pxPerNm, v.cy - y * v.pxPerNm]