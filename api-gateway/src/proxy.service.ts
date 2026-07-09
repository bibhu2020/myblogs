import { Injectable, HttpException } from '@nestjs/common';
import axios, { AxiosRequestConfig } from 'axios';
import FormData from 'form-data';

const SERVICES = {
  auth: 'http://localhost:3001',
  blog: 'http://localhost:3002',
  media: 'http://localhost:3003',
};

@Injectable()
export class ProxyService {
  async forward(service: keyof typeof SERVICES, path: string, method: string, data?: any, headers?: any) {
    const url = `${SERVICES[service]}${path}`;
    const config: AxiosRequestConfig = { method: method as any, url, data, headers: headers || {}, timeout: 30000 };
    try {
      const response = await axios(config);
      return response.data;
    } catch (err) {
      const status = err.response?.status || 500;
      const message = err.response?.data?.message || err.message;
      throw new HttpException(message, status);
    }
  }

  async forwardWithFile(path: string, file: Express.Multer.File, body: any, authHeader: string, query?: Record<string, string>) {
    const form = new FormData();
    form.append('file', file.buffer, { filename: file.originalname, contentType: file.mimetype });
    if (body.alt) form.append('alt', body.alt);
    const qs = query && Object.keys(query).length ? `?${new URLSearchParams(query).toString()}` : '';
    const url = `${SERVICES.media}${path}${qs}`;
    try {
      const response = await axios.post(url, form, {
        headers: { ...form.getHeaders(), Authorization: authHeader },
        timeout: 30000,
      });
      return response.data;
    } catch (err) {
      const status = err.response?.status || 500;
      throw new HttpException(err.response?.data?.message || err.message, status);
    }
  }
}
