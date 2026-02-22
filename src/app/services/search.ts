import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

const SEARCH_CACHE_KEY = 'searchCache';

export type ItemRow = [string, string]; // [name, price]

export interface SearchResultPayload {
  query: string;
  key: string;
  results: {
    sainsburys: ItemRow[];
    homebargains: ItemRow[];
    morrisons: ItemRow[];
  };
}

// For backwards compatibility / convenience
export interface CrawlerItem {
  title: string;
  unitPrice: number;
  market: string;
  quantity: number;
}

export type SearchResponse = SearchResultPayload;  // alias

type SearchCache = Record<string, SearchResultPayload>;

function normalizeQuery(q: string): string {
  return q
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, ' ');
}

@Injectable({ providedIn: 'root' })
export class Search {
  private lastResult: SearchResultPayload | null = null;

  constructor(private http: HttpClient) {}

  private readCache(): SearchCache {
    try {
      const raw = localStorage.getItem(SEARCH_CACHE_KEY);
      return raw ? (JSON.parse(raw) as SearchCache) : {};
    } catch {
      return {};
    }
  }

  private writeCache(cache: SearchCache): void {
    try {
      localStorage.setItem(SEARCH_CACHE_KEY, JSON.stringify(cache));
    } catch {
      // ignore
    }
  }

  search(query: string): Observable<SearchResultPayload> {
    const trimmed = query.trim();
    if (!trimmed) {
      return of({
        query: '',
        key: '',
        results: { sainsburys: [], homebargains: [], morrisons: [] },
      });
    }

    const key = normalizeQuery(trimmed);
    const cache = this.readCache();

    if (cache[key]) {
      this.lastResult = cache[key];
      return of(cache[key]);
    }

    return this.http
      .get<SearchResultPayload>('http://localhost:8000/api/search', {
        params: { q: trimmed },
      })
      .pipe(
        tap((resp) => {
          const updated: SearchCache = {
            ...cache,
            [resp.key]: resp,
          };
          this.writeCache(updated);
          this.lastResult = resp;
        }),
      );
  }

  getLastResult(): SearchResultPayload | null {
    return this.lastResult;
  }
}