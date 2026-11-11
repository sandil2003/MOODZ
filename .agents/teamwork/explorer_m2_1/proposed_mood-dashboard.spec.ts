import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MoodDashboard } from './mood-dashboard';

describe('MoodDashboard', () => {
  let component: MoodDashboard;
  let fixture: ComponentFixture<MoodDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MoodDashboard],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MoodDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture?.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
