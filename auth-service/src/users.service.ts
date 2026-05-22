import { Injectable, ConflictException, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User, UserRole } from './user.entity';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class UsersService {
  constructor(@InjectRepository(User) private userRepo: Repository<User>) {}

  async findAll() {
    return this.userRepo.find({ select: ['id','email','name','role','bio','avatar','isActive','createdAt'] });
  }

  async findOne(id: number) {
    const user = await this.userRepo.findOne({ where: { id }, select: ['id','email','name','role','bio','avatar','isActive','createdAt'] });
    if (!user) throw new NotFoundException('User not found');
    return user;
  }

  async create(dto: { email: string; password: string; name: string; role?: UserRole; bio?: string }) {
    const existing = await this.userRepo.findOne({ where: { email: dto.email } });
    if (existing) throw new ConflictException('Email already exists');
    const hash = await bcrypt.hash(dto.password, 10);
    const user = this.userRepo.create({ ...dto, password: hash, role: dto.role || UserRole.GUEST });
    const saved = await this.userRepo.save(user);
    const { password: _, ...result } = saved;
    return result;
  }

  async update(id: number, dto: Partial<{ name: string; bio: string; avatar: string; isActive: boolean; password: string }>) {
    const user = await this.userRepo.findOne({ where: { id } });
    if (!user) throw new NotFoundException('User not found');
    if (dto.password) dto.password = await bcrypt.hash(dto.password, 10);
    Object.assign(user, dto);
    const saved = await this.userRepo.save(user);
    const { password: _, ...result } = saved;
    return result;
  }

  async remove(id: number) {
    const user = await this.userRepo.findOne({ where: { id } });
    if (!user) throw new NotFoundException('User not found');
    await this.userRepo.remove(user);
    return { message: 'User deleted' };
  }
}
