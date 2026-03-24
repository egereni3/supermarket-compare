import { Component } from '@angular/core';
import { NgForOf, NgIf, AsyncPipe, CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Basket, BasketItem } from '../../services/basket';
import { Observable, firstValueFrom } from 'rxjs';
import { Auth } from '../../auth/auth';

declare const google: any;

interface LatLngLiteral {
  lat: number;
  lng: number;
}

interface MarketCandidateStop {
  market: string;
  location: LatLngLiteral;
}

@Component({
  selector: 'app-account',
  standalone: true,
  imports: [NgForOf, NgIf, AsyncPipe, CommonModule, FormsModule],
  templateUrl: './account.html',
  styleUrls: ['./account.scss'],
})
export class Account {
  items$: Observable<BasketItem[]>;
  mapError: string | null = null;
  routeSummary: string | null = null;
  loadingRoute = false;
  mapReady = false;
  private map: any | null = null;
  private directionsRenderer: any | null = null;
  private static googleMapsLoader: Promise<void> | null = null;

  // profile form fields
  currentEmail = '';
  newEmail = '';
  emailPassword = '';
  emailError: string | null = null;
  emailMessage: string | null = null;
  showEmailForm = false;

  currentPasswordForChange = '';
  newPassword = '';
  confirmNewPassword = '';
  passError: string | null = null;
  passMessage: string | null = null;
  showPasswordForm = false;

  constructor(private basket: Basket, private auth: Auth) {
    this.items$ = this.basket.items$;
    const user = this.auth.getUser();
    this.currentEmail = user?.email ?? '';
  }

  remove(id: string): void {
    this.basket.remove(id);
  }

  clear(): void {
    this.basket.clear();
  }

  // Verify current password by attempting login, then update local email
  updateEmail(): void {
    this.emailError = null;
    this.emailMessage = null;
    if (!this.newEmail.trim() || !this.emailPassword.trim()) {
      this.emailError = 'New email and current password are required.';
      return;
    }
    // verify current password
    this.auth.login(this.currentEmail, this.emailPassword).subscribe({
      next: (resp) => {
        if (!resp.success) {
          this.emailError = resp.error ?? 'Current password incorrect.';
          return;
        }
        const userId = this.auth.getUser()?.id;
        if (!userId) {
          this.emailError = 'User not found locally.';
          return;
        }
        // call server to update email
        this.auth.updateUser(userId, { email: this.newEmail.trim() }).subscribe({
          next: (uResp: any) => {
            if (!uResp.success) {
              this.emailError = uResp.error ?? 'Update failed.';
              return;
            }
            // update local storage and UI
            this.auth.updateLocalEmail(this.newEmail.trim());
            this.currentEmail = this.newEmail.trim();
            this.newEmail = '';
            this.emailPassword = '';
            this.emailMessage = 'Email updated successfully.';
            this.showEmailForm = false;
          },
          error: (err: any) => {
            this.emailError = err?.error?.error ?? err?.message ?? 'Server error.';
          },
        });
      },
      error: (err) => {
        this.emailError = err?.error?.error ?? err?.message ?? 'Server error.';
      },
    });
  }

  // Verify current password then validate new password and show success message
  updatePassword(): void {
    this.passError = null;
    this.passMessage = null;
    if (!this.currentPasswordForChange.trim() || !this.newPassword.trim() || !this.confirmNewPassword.trim()) {
      this.passError = 'All password fields are required.';
      return;
    }
    if (this.newPassword !== this.confirmNewPassword) {
      this.passError = 'New passwords do not match.';
      return;
    }
    if (this.newPassword.length < 6 || !/[A-Z]/.test(this.newPassword) || !/[0-9]/.test(this.newPassword)) {
      this.passError = 'Password must be at least 6 characters, contain an uppercase letter and a number.';
      return;
    }

    // verify current password
    this.auth.login(this.currentEmail, this.currentPasswordForChange).subscribe({
      next: (resp) => {
        if (!resp.success) {
          this.passError = resp.error ?? 'Current password incorrect.';
          return;
        }
        const userId = this.auth.getUser()?.id;
        if (!userId) {
          this.passError = 'User not found locally.';
          return;
        }
        // call server to update password
        this.auth.updateUser(userId, { password: this.newPassword }).subscribe({
          next: (uResp: any) => {
            if (!uResp.success) {
              this.passError = uResp.error ?? 'Password update failed.';
              return;
            }
            this.currentPasswordForChange = '';
            this.newPassword = '';
            this.confirmNewPassword = '';
            this.passMessage = 'Password updated successfully.';
            this.showPasswordForm = false;
          },
          error: (err: any) => {
            this.passError = err?.error?.error ?? err?.message ?? 'Server error.';
          },
        });
      },
      error: (err) => {
        this.passError = err?.error?.error ?? err?.message ?? 'Server error.';
      },
    });
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

  async buildBasketRoute(): Promise<void> {
    this.mapError = null;
    this.routeSummary = null;
    this.loadingRoute = true;
    this.mapReady = false;

    try {
      const items = await firstValueFrom(this.items$);
      const uniqueMarkets = this.getUniqueMarkets(items);

      if (!uniqueMarkets.length) {
        this.mapError = 'Add products to the basket before planning a route.';
        return;
      }

      await this.withTimeout(this.loadGoogleMaps(), 15000, 'Loading Google Maps took too long.');
      const userLocation = await this.withTimeout(
        this.getCurrentLocation(),
        20000,
        'Location request timed out. Please allow location access and try again.'
      );
      const mapHost = this.getMapHost();
      if (!mapHost) {
        this.mapError = 'Map container not found.';
        return;
      }

      const marketStops = await this.withTimeout(
        this.findMarketStops(userLocation, uniqueMarkets),
        20000,
        'Store lookup timed out. Please try again.'
      );
      if (!marketStops.length) {
        this.mapError = 'Could not find nearby stores for the selected basket shops.';
        return;
      }

      // Ensure map container is visible before Google map initialization.
      this.mapReady = true;
      await this.waitForDomPaint();
      this.initializeMap(mapHost, userLocation);
      await this.withTimeout(this.renderRoute(userLocation, marketStops), 20000, 'Route building timed out.');
    } catch (error: any) {
      this.mapError = error?.message ?? 'Could not build your route right now.';
      this.mapReady = false;
    } finally {
      this.loadingRoute = false;
    }
  }

  private getUniqueMarkets(items: BasketItem[]): string[] {
    return [...new Set(items.map((item) => item.market.trim()).filter((name) => !!name))];
  }

  private getMapHost(): HTMLElement | null {
    return document.getElementById('basket-route-map');
  }

  private loadGoogleMaps(): Promise<void> {
    const apiKey = (window as any).GOOGLE_MAPS_API_KEY as string | undefined;
    if (!apiKey) {
      return Promise.reject(
        new Error('Google Maps API key is missing. Set window.GOOGLE_MAPS_API_KEY in index.html.')
      );
    }

    if ((window as any).google?.maps) {
      return Promise.resolve();
    }

    if (Account.googleMapsLoader) {
      return Account.googleMapsLoader;
    }

    Account.googleMapsLoader = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load Google Maps API script.'));
      document.head.appendChild(script);
    });

    return Account.googleMapsLoader;
  }

  private getCurrentLocation(): Promise<LatLngLiteral> {
    if (!navigator.geolocation) {
      return Promise.reject(new Error('Geolocation is not supported by this browser.'));
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) =>
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          }),
        (error) => {
          const message =
            error.code === error.PERMISSION_DENIED
              ? 'Location permission denied. Please allow location access and try again.'
              : 'Could not access your location.';
          reject(new Error(message));
        },
        { enableHighAccuracy: true, timeout: 15000 }
      );
    });
  }

  private findMarketStops(origin: LatLngLiteral, markets: string[]): Promise<LatLngLiteral[]> {
    const service = new google.maps.places.PlacesService(document.createElement('div'));

    const lookups = markets.map(
      (market) =>
        new Promise<MarketCandidateStop[]>((resolve) => {
          const timeoutId = window.setTimeout(() => resolve([]), 8000);
          service.nearbySearch(
            {
              location: origin,
              radius: 25000,
              keyword: market,
            },
            (results: any[], status: string) => {
              window.clearTimeout(timeoutId);
              if (status !== google.maps.places.PlacesServiceStatus.OK || !results?.length) {
                resolve([]);
                return;
              }

              // Keep a few nearest branches per market so we can optimize globally.
              const candidates: MarketCandidateStop[] = results
                .slice(0, 3)
                .map((result) => result?.geometry?.location)
                .filter((location) => !!location)
                .map((location) => ({
                  market,
                  location: { lat: location.lat(), lng: location.lng() },
                }));

              resolve(candidates);
            }
          );
        })
    );

    return Promise.all(lookups).then((candidateGroups) => this.selectBestMarketStops(origin, candidateGroups));
  }

  private selectBestMarketStops(origin: LatLngLiteral, candidateGroups: MarketCandidateStop[][]): LatLngLiteral[] {
    const validGroups = candidateGroups.filter((group) => group.length > 0);
    if (!validGroups.length) {
      return [];
    }

    let bestScore = Number.POSITIVE_INFINITY;
    let bestStops: LatLngLiteral[] | null = null;

    const evaluateCombination = (stops: LatLngLiteral[]) => {
      const permutations = this.permuteStops(stops);
      for (const perm of permutations) {
        const score = this.routeDistanceScore(origin, perm);
        if (score < bestScore) {
          bestScore = score;
          bestStops = perm;
        }
      }
    };

    const buildCombinations = (groupIndex: number, selected: LatLngLiteral[]) => {
      if (groupIndex >= validGroups.length) {
        evaluateCombination(selected);
        return;
      }

      for (const candidate of validGroups[groupIndex]) {
        buildCombinations(groupIndex + 1, [...selected, candidate.location]);
      }
    };

    buildCombinations(0, []);
    return bestStops ?? validGroups.map((group) => group[0].location);
  }

  private permuteStops(stops: LatLngLiteral[]): LatLngLiteral[][] {
    if (stops.length <= 1) {
      return [stops];
    }

    const permutations: LatLngLiteral[][] = [];
    const used = new Array<boolean>(stops.length).fill(false);
    const current: LatLngLiteral[] = [];

    const walk = () => {
      if (current.length === stops.length) {
        permutations.push([...current]);
        return;
      }
      for (let i = 0; i < stops.length; i += 1) {
        if (used[i]) continue;
        used[i] = true;
        current.push(stops[i]);
        walk();
        current.pop();
        used[i] = false;
      }
    };

    walk();
    return permutations;
  }

  private routeDistanceScore(origin: LatLngLiteral, orderedStops: LatLngLiteral[]): number {
    if (!orderedStops.length) {
      return 0;
    }

    let score = 0;
    let previous = origin;

    for (const stop of orderedStops) {
      score += this.haversineKm(previous, stop);
      previous = stop;
    }

    return score;
  }

  private haversineKm(a: LatLngLiteral, b: LatLngLiteral): number {
    const toRad = (value: number) => (value * Math.PI) / 180;
    const earthRadiusKm = 6371;
    const dLat = toRad(b.lat - a.lat);
    const dLng = toRad(b.lng - a.lng);
    const lat1 = toRad(a.lat);
    const lat2 = toRad(b.lat);

    const h =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) * Math.sin(dLng / 2);

    return 2 * earthRadiusKm * Math.asin(Math.sqrt(h));
  }

  private initializeMap(container: HTMLElement, center: LatLngLiteral): void {
    if (!this.map) {
      this.map = new google.maps.Map(container, {
        center,
        zoom: 11,
      });
    } else {
      this.map.setCenter(center);
      this.map.setZoom(11);
    }

    if (!this.directionsRenderer) {
      this.directionsRenderer = new google.maps.DirectionsRenderer({
        suppressMarkers: false,
        preserveViewport: false,
      });
      this.directionsRenderer.setMap(this.map);
    }
  }

  private renderRoute(origin: LatLngLiteral, stops: LatLngLiteral[]): Promise<void> {
    if (!this.map || !this.directionsRenderer) {
      return Promise.reject(new Error('Map not initialized.'));
    }

    const directionsService = new google.maps.DirectionsService();
    const destination = stops[stops.length - 1];
    const intermediateStops = stops.slice(0, -1);
    const waypoints = intermediateStops.map((stop) => ({ location: stop, stopover: true }));

    return new Promise((resolve, reject) => {
      directionsService.route(
        {
          origin,
          destination,
          waypoints,
          optimizeWaypoints: false,
          travelMode: google.maps.TravelMode.DRIVING,
        },
        (result: any, status: string) => {
          if (status !== google.maps.DirectionsStatus.OK || !result) {
            reject(new Error('Directions request failed.'));
            return;
          }

          this.directionsRenderer.setDirections(result);
          const legCount = result.routes?.[0]?.legs?.length ?? 0;
          this.routeSummary = `Route ready: ${stops.length} shop stop(s), ${legCount} travel segment(s).`;
          resolve();
        }
      );
    });
  }

  private waitForDomPaint(): Promise<void> {
    return new Promise((resolve) => requestAnimationFrame(() => resolve()));
  }

  private withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const timeoutId = window.setTimeout(() => reject(new Error(message)), timeoutMs);
      promise
        .then((value) => resolve(value))
        .catch((error) => reject(error))
        .finally(() => window.clearTimeout(timeoutId));
    });
  }

}