import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MoodAgent } from './mood-agent';

describe('MoodAgent', () => {
  let component: MoodAgent;
  let fixture: ComponentFixture<MoodAgent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MoodAgent],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MoodAgent);
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
