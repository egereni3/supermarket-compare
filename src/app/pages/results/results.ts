import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgForOf, NgIf, AsyncPipe, CommonModule } from '@angular/common';
import { Search, SearchResultPayload, ItemRow } from '../../services/search';
import { Auth } from '../../auth/auth';
import { FormsModule } from '@angular/forms';
import { Basket, BasketItem } from '../../services/basket';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [NgForOf, NgIf, FormsModule, AsyncPipe, CommonModule],
  templateUrl: './results.html',
  styleUrls: ['./results.scss'],
})
export class Results implements OnInit {
  query = '';
  results: SearchResultPayload['results'] | null = null;
  loading = false;
  error: string | null = null;
  items$: Observable<BasketItem[]>;
  animatingKeys = new Set<string>();

  quantities: Record<string, number[]> = {
    sainsburys: [],
    homebargains: [],
    morrisons: [],
  };

  constructor(
    private route: ActivatedRoute,
    private search: Search,
    private basket: Basket,
    private auth: Auth,
    private router: Router
    
  ) {
    this.items$ = this.basket.items$;
    const user = this.auth.getUser();

  }

  ngOnInit(): void {
    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/home']);
      return;
    }

    type Store = 'sainsburys' | 'homebargains' | 'morrisons';

    this.route.queryParams.subscribe((params) => {
      const q = params['q'] ?? '';
      this.query = q;

      const cached = this.search.getLastResult();
      if (cached && cached.query === q) {
        this.results = cached.results;

        if (this.results) { 
          const stores: Store[] = ['sainsburys', 'homebargains', 'morrisons'];
          stores.forEach(store => {
            if (this.results && this.results[store]?.length) {
              this.results[store].forEach((_, i) => {
                if (!this.quantities[store][i]) {
                  this.quantities[store][i] = 1;
                }
              });
            }
          });
        }

        return;
      }

      if (q) {
        this.loading = true;
        this.search.search(q).subscribe({
          next: (resp: SearchResultPayload) => {
            this.loading = false;
            this.results = resp.results;

            if (this.results) {
              const stores: Store[] = ['sainsburys', 'homebargains', 'morrisons'];
              stores.forEach(store => {
                if (this.results && this.results[store]?.length) {
                  this.results[store].forEach((_, i) => {
                    if (!this.quantities[store][i]) {
                      this.quantities[store][i] = 1;
                    }
                  });
                }
              });
            }
          },
          error: () => {
            this.loading = false;
          },
        });
      }
    });
  }

  max1(value: number): number {
    return Math.max(1, value);
  }

  normalizeQuantity(store: string, index: number): void {
    if (!this.quantities[store][index] || this.quantities[store][index] < 1) {
      this.quantities[store][index] = 1;
    }
  }

  getItemKey(item: ItemRow, market: string, index: number): string {
    return `${market}:${item[0]}:${index}`;
  }

  addToBasket(item: ItemRow, market: string, quantity: number): void {
    const [title, priceStr] = item;

    let unitPrice = 0;
    const normalized = priceStr.trim().toLowerCase();

    if (normalized.endsWith('p')) {
      const pence = parseFloat(normalized.replace(/[^0-9.]/g, ''));
      unitPrice = pence / 100;
    } else {
      unitPrice = parseFloat(normalized.replace(/[^0-9.]/g, '')) || 0;
    }

    const basketItem = {
      title,
      unitPrice,
      market,
      quantity,
    };

    this.basket.add(basketItem, quantity); 
  }

  onAddClick(item: ItemRow, market: string, index: number): void {
    const key = this.getItemKey(item, market, index);

    const quantity = Math.max(1, this.quantities[market]?.[index] ?? 1);

    const triggerAnimation = () => {
      this.animatingKeys.add(key);

      this.addToBasket(item, market, quantity);

      setTimeout(() => this.animatingKeys.delete(key), 600);
    };

    if (this.animatingKeys.has(key)) {
      this.animatingKeys.delete(key);
      setTimeout(triggerAnimation, 20);
    } else {
      triggerAnimation();
    }
  }

  isAnimating(item: ItemRow, market: string, index: number): boolean {
    return this.animatingKeys.has(this.getItemKey(item, market, index));
  }

    get isLoggedIn(): boolean {
    return this.auth.isLoggedIn();
  }

  onSearch(): void {
    this.error = null;
    const trimmed = this.query.trim();
    if (!trimmed) {
      this.error = 'Please enter a query.';
      return;
    }

    this.loading = true;
    this.search.search(trimmed).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/results'], { queryParams: { q: trimmed } });
      },
      error: () => {
        this.loading = false;
        this.error = 'Search failed. Please try again.';
      },
    });
  }

  remove(id: string): void {
    this.basket.remove(id);
  }

  clear(): void {
    this.basket.clear();
  }

    increaseQuantity(item: BasketItem) {
    this.updateQuantity(item, item.quantity + 1);
  }

  decreaseQuantity(item: BasketItem) {
    if (item.quantity > 1) {
      this.updateQuantity(item, item.quantity - 1);
    }
  }

  onQuantityInputChange(item: BasketItem, value: string | number) {
    let qty = Number(value);
    if (isNaN(qty) || qty < 1) {
      qty = 1;
    }

    this.updateQuantity(item, qty);
  }

  updateQuantity(item: BasketItem, quantity: number) {
    if (quantity < 1) quantity = 1;

    this.basket.updateQuantity(item.id, quantity);
  }

  getBasketTotal(items: BasketItem[]): number {
    return items.reduce((total, item) => total + item.unitPrice * item.quantity, 0);
  }
}