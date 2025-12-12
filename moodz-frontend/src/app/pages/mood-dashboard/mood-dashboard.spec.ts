import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MoodDashboard } from './mood-dashboard';

describe('MoodDashboard', () => {
  let component: MoodDashboard;
  let fixture: ComponentFixture<MoodDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MoodDashboard]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MoodDashboard);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
