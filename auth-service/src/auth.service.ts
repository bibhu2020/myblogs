import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User, UserRole } from './user.entity';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(User) private userRepo: Repository<User>,
    private jwtService: JwtService,
  ) {}

  async validateUser(email: string, password: string): Promise<any> {
    const user = await this.userRepo.findOne({ where: { email, isActive: true } });
    if (user && await bcrypt.compare(password, user.password)) {
      const { password: _, ...result } = user;
      return result;
    }
    return null;
  }

  async login(user: any) {
    const payload = { sub: user.id, email: user.email, role: user.role, name: user.name };
    return {
      access_token: this.jwtService.sign(payload),
      user: { id: user.id, email: user.email, name: user.name, role: user.role, avatar: user.avatar, bio: user.bio },
    };
  }

  async seed() {
    const count = await this.userRepo.count();
    if (count === 0) {
      const hash = await bcrypt.hash('admin123', 10);
      await this.userRepo.save({
        email: 'admin@myblogs.com',
        password: hash,
        name: 'Site Admin',
        role: UserRole.ADMIN,
        bio: 'Administrator of MyBlogs',
        isActive: true,
      });
      console.log('Admin user seeded: admin@myblogs.com / admin123');
    }
  }
}
