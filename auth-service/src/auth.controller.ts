import { Controller, Post, Body, UseGuards, Request, Get, OnModuleInit } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { AuthService } from './auth.service';

@Controller('auth')
export class AuthController implements OnModuleInit {
  constructor(private authService: AuthService) {}

  async onModuleInit() {
    await this.authService.seed();
  }

  @UseGuards(AuthGuard('local'))
  @Post('login')
  async login(@Request() req) {
    return this.authService.login(req.user);
  }

  @Get('verify')
  @UseGuards(AuthGuard('jwt'))
  verify(@Request() req) {
    return req.user;
  }
}
