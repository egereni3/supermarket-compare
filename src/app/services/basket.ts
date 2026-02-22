import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { CrawlerItem } from './search';

const BASKET_KEY = 'basket';

export interface BasketItem extends CrawlerItem {
  id: string; // can be generated from title + market, etc.
  quantity: number;
}

@Injectable({
  providedIn: 'root',
})
export class Basket {
  private readonly itemsSubject = new BehaviorSubject<BasketItem[]>(this.read());
  readonly items$ = this.itemsSubject.asObservable();

  add(item: CrawlerItem, quantity: number = 1): void {
    const current = this.itemsSubject.value;
    const id = `${item.market}:${item.title}:${Date.now()}:${Math.random()
      .toString(36)
      .slice(2, 7)}`;

    const updated: BasketItem[] = [...current, { ...item, id, quantity }];
    this.itemsSubject.next(updated);
    this.write(updated);
  }

  updateQuantity(id: string, quantity: number): void {
    if (quantity < 1) quantity = 1; // minimum 1

    const updated = this.itemsSubject.value.map((item) =>
      item.id === id ? { ...item, quantity } : item
    );
    this.itemsSubject.next(updated);
    this.write(updated);
  }

  remove(id: string): void {
    const updated = this.itemsSubject.value.filter((i) => i.id !== id);
    this.itemsSubject.next(updated);
    this.write(updated);
  }

  clear(): void {
    this.itemsSubject.next([]);
    this.write([]);
  }

  private read(): BasketItem[] {
    try {
      const raw = localStorage.getItem(BASKET_KEY);
      return raw ? (JSON.parse(raw) as BasketItem[]) : [];
    } catch {
      return [];
    }
  }

  private write(items: BasketItem[]): void {
    try {
      localStorage.setItem(BASKET_KEY, JSON.stringify(items));
    } catch {
      // ignore
    }
  }
}