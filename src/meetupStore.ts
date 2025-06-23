import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { Meetup } from './types/meetup';

const DATA_PATH = path.join(__dirname, '..', 'data', 'meetups.json');

export class MeetupStore {
  private meetups: Record<string, Meetup> = {};

  constructor() {
    this.load();
  }

  private load() {
    if (fs.existsSync(DATA_PATH)) {
      this.meetups = JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8'));
    }
  }

  private save() {
    fs.writeFileSync(DATA_PATH, JSON.stringify(this.meetups, null, 2));
  }

  createMeetup(name: string, points: number): Meetup {
    const id = crypto.randomBytes(4).toString('hex'); // короткий хеш
    const meetup: Meetup = {
      id,
      name,
      date: new Date().toISOString(),
      active: false,
      points,
    };
    this.meetups[id] = meetup;
    this.save();
    return meetup;
  }

  activate(id: string) {
    if (this.meetups[id]) {
      this.meetups[id].active = true;
      this.save();
    }
  }

  deactivate(id: string) {
    if (this.meetups[id]) {
      this.meetups[id].active = false;
      this.save();
    }
  }

  get(id: string): Meetup | undefined {
    return this.meetups[id];
  }

  list(): Meetup[] {
    return Object.values(this.meetups).sort((a, b) => b.date.localeCompare(a.date));
  }
}
