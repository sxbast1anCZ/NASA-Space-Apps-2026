// A small flat-shaded house (walls, gable roof, chimney) for deck.gl's SimpleMeshLayer.
// Unit size: 1 wide, about 1.1 high, z up. Each triangle has its own vertices so the faces look crisp.

type V = [number, number, number]

const tris: V[][] = []
const quad = (a: V, b: V, c: V, d: V) => { tris.push([a, b, c], [a, c, d]) }
function box(x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, top = true) {
  quad([x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1])
  quad([x1, y1, z0], [x0, y1, z0], [x0, y1, z1], [x1, y1, z1])
  quad([x0, y1, z0], [x0, y0, z0], [x0, y0, z1], [x0, y1, z1])
  quad([x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1])
  if (top) quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1])
}

box(-0.5, -0.4, 0, 0.5, 0.4, 0.6, false) // walls
tris.push([[-0.5, -0.4, 0.6], [-0.5, 0.4, 0.6], [-0.5, 0, 1.0]]) // gable ends
tris.push([[0.5, 0.4, 0.6], [0.5, -0.4, 0.6], [0.5, 0, 1.0]])
quad([-0.58, -0.5, 0.55], [0.58, -0.5, 0.55], [0.58, 0, 1.02], [-0.58, 0, 1.02]) // roof slopes
quad([0.58, 0.5, 0.55], [-0.58, 0.5, 0.55], [-0.58, 0, 1.02], [0.58, 0, 1.02])
quad([-0.58, -0.5, 0.55], [-0.58, 0, 1.02], [0.58, 0, 1.02], [0.58, -0.5, 0.55]) // roof undersides
quad([0.58, 0.5, 0.55], [0.58, 0, 1.02], [-0.58, 0, 1.02], [-0.58, 0.5, 0.55])
box(0.18, 0.12, 0.7, 0.32, 0.26, 1.12) // chimney

const positions: number[] = [], normals: number[] = []
for (const [a, b, c] of tris) {
  const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]]
  const n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
  const l = Math.hypot(n[0], n[1], n[2]) || 1
  for (const p of [a, b, c]) { positions.push(...p); normals.push(n[0] / l, n[1] / l, n[2] / l) }
}

export const HOUSE_MESH = {
  attributes: {
    positions: { value: new Float32Array(positions), size: 3 },
    normals: { value: new Float32Array(normals), size: 3 },
  },
}
