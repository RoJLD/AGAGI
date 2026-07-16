import { describe, it, expect } from "vitest";
import {
  buildQueueItems,
  mergeQueue,
  queueTick,
  applyStartFailure,
  stopQueue,
  queueCounts,
  type QueueState,
} from "./queue";
import type { RunConfig, QueuedRun } from "../types";

const config: RunConfig = {
  script_name: "main_biosphere.py",
  world_type: "stoneage",
  base_seed: 10,
  n_seeds: 3,
  mutation_rate: null,
  variable_tested: "x",
  tags: [],
};

function item(id: string, seed: number, status: QueuedRun["status"]): QueuedRun {
  return { id, seed, status };
}

describe("buildQueueItems", () => {
  it("construit n_seeds items pending avec id=script#seed", () => {
    const items = buildQueueItems(config);
    expect(items).toEqual([
      { id: "main_biosphere.py#10", seed: 10, status: "pending" },
      { id: "main_biosphere.py#11", seed: 11, status: "pending" },
      { id: "main_biosphere.py#12", seed: 12, status: "pending" },
    ]);
  });
});

describe("mergeQueue", () => {
  it("dédup par id, préserve l'ordre, append les nouveaux", () => {
    const prev = [item("a#0", 0, "done"), item("a#1", 1, "pending")];
    const incoming = [item("a#1", 1, "pending"), item("a#2", 2, "pending")];
    expect(mergeQueue(prev, incoming)).toEqual([
      item("a#0", 0, "done"),
      item("a#1", 1, "pending"),
      item("a#2", 2, "pending"),
    ]);
  });
});

describe("queueTick", () => {
  it("file inactive => aucun effet, état inchangé", () => {
    const state: QueueState = { items: [item("a#0", 0, "pending")], running: false, current: null };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "none" });
    expect(next).toBe(state);
  });

  it("idle + pending + sandbox libre => effet start, item->running, current posé", () => {
    const state: QueueState = { items: [item("a#0", 0, "pending")], running: true, current: null };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "start", id: "a#0", seed: 0 });
    expect(next.items[0].status).toBe("running");
    expect(next.current).toEqual({ id: "a#0", sawRunning: false });
  });

  it("current + sandbox running => sawRunning=true, effet none", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: false },
    };
    const { state: next, effect } = queueTick(state, true);
    expect(effect).toEqual({ type: "none" });
    expect(next.current).toEqual({ id: "a#0", sawRunning: true });
    expect(next.items[0].status).toBe("running");
  });

  it("current + sawRunning + sandbox libre => item->done par id, current cleared", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: true },
    };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "none" });
    expect(next.items[0].status).toBe("done");
    expect(next.current).toBeNull();
  });

  it("current + PAS sawRunning + sandbox libre => patiente (pas de done prématuré)", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: false },
    };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "none" });
    expect(next.items[0].status).toBe("running");
    expect(next.current).toEqual({ id: "a#0", sawRunning: false });
  });

  it("pas de current + sandbox running (ad hoc) => attente, pas de start", () => {
    const state: QueueState = { items: [item("a#0", 0, "pending")], running: true, current: null };
    const { state: next, effect } = queueTick(state, true);
    expect(effect).toEqual({ type: "none" });
    expect(next.items[0].status).toBe("pending");
    expect(next.current).toBeNull();
  });

  it("plus aucun pending => effet complete, running=false", () => {
    const state: QueueState = { items: [item("a#0", 0, "done")], running: true, current: null };
    const { state: next, effect } = queueTick(state, false);
    expect(effect).toEqual({ type: "complete" });
    expect(next.running).toBe(false);
  });

  it("deux items même seed, ids différents => seul l'id lancé passe done", () => {
    const state: QueueState = {
      items: [item("a#5", 5, "running"), item("b#5", 5, "pending")],
      running: true,
      current: { id: "a#5", sawRunning: true },
    };
    const { state: next } = queueTick(state, false);
    expect(next.items[0].status).toBe("done"); // a#5 (lancé)
    expect(next.items[1].status).toBe("pending"); // b#5 intact
  });
});

describe("applyStartFailure", () => {
  it("seul l'id échoué passe error, current cleared", () => {
    const state: QueueState = {
      items: [item("a#5", 5, "running"), item("b#5", 5, "pending")],
      running: true,
      current: { id: "a#5", sawRunning: false },
    };
    const next = applyStartFailure(state, "a#5");
    expect(next.items[0].status).toBe("error");
    expect(next.items[1].status).toBe("pending");
    expect(next.current).toBeNull();
  });
});

describe("stopQueue", () => {
  it("running=false, current=null", () => {
    const state: QueueState = {
      items: [item("a#0", 0, "running")],
      running: true,
      current: { id: "a#0", sawRunning: true },
    };
    const next = stopQueue(state);
    expect(next.running).toBe(false);
    expect(next.current).toBeNull();
  });
});

describe("queueCounts", () => {
  it("tally par statut (clés absentes pour statuts absents)", () => {
    const items = [item("a#0", 0, "pending"), item("a#1", 1, "pending"), item("a#2", 2, "done")];
    expect(queueCounts(items)).toEqual({ pending: 2, done: 1 });
  });
});
