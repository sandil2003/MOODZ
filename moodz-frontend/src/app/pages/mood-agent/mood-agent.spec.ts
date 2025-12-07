import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MoodAgent } from './mood-agent';

describe('MoodAgent', () => {
  let component: MoodAgent;
  let fixture: ComponentFixture<MoodAgent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MoodAgent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MoodAgent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
