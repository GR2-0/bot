import fs from 'fs';
import path from 'path';

const DATA_PATH = path.join(__dirname, '..', 'data', 'users.json');

interface UserData {
  id: number;
  username?: string;
  name: string;
}

export class UserStore {
  private users: Record<number, UserData> = {};

  constructor() {
    this.load();
  }

  private load() {
    if (fs.existsSync(DATA_PATH)) {
      this.users = JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8'));
    }
  }

  private save() {
    fs.writeFileSync(DATA_PATH, JSON.stringify(this.users, null, 2));
  }

  getUser(id: number): UserData | undefined {
    return this.users[id];
  }

  addUser({ id, username, name }: { id: number; username?: string; name: string }) {
    if (!this.users[id]) {
      this.users[id] = {
        id,
        username,
        name,
      };
      this.save();
    }
  }
}
