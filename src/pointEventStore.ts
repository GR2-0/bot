import fs from 'fs';
import path from 'path';
import { PointEvent } from './types/pointEvent';

const DATA_PATH = path.join(__dirname, '..', 'data', 'point_events.json');

export class PointEventStore {
  private events: PointEvent[] = [];

  constructor() {
    this.load();
  }

  private load() {
    if (fs.existsSync(DATA_PATH)) {
      this.events = JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8'));
    }
  }

  private save() {
    fs.writeFileSync(DATA_PATH, JSON.stringify(this.events, null, 2));
  }

  getAll(): PointEvent[] {
    return this.events;
  }

  add(event: PointEvent) {
    this.events.push(event);
    this.save();
  }

  hasEvent(userId: number, type: string, meetupId?: string): boolean {
    return this.events.some(e =>
      e.userId === userId &&
      e.type === type &&
      (meetupId ? e.meetupId === meetupId : true)
    );
  }

  getUserPoints(userId: number): number {
    return this.events
      .filter(e => e.userId === userId)
      .reduce((sum, e) => sum + e.points, 0);
  }

  getUserEvents(userId: number): PointEvent[] {
    return this.events.filter(e => e.userId === userId);
  }
}
